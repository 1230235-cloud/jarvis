import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:flutter_background/flutter_background.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'dart:io' show Platform, Process;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (Platform.isAndroid) {
    await _initBackgroundService();
  }
  runApp(const NemApp());
}

Future<void> _initBackgroundService() async {
  try {
    const androidConfig = FlutterBackgroundAndroidConfig(
      notificationTitle: "Nem Assistant",
      notificationText: "Nem está escuchando en segundo plano...",
      notificationIcon: AndroidResource(name: 'background_icon', defType: 'drawable'),
    );
    bool hasPermissions = await FlutterBackground.hasPermissions;
    if (!hasPermissions) {
      await Permission.microphone.request();
      await Permission.notification.request();
    }
    await FlutterBackground.initialize(androidConfig: androidConfig);
    await FlutterBackground.enableBackgroundExecution();
  } catch (e) {
    debugPrint("Background init skipped/failed: $e");
  }
}

class NemApp extends StatelessWidget {
  const NemApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Nem AI Client',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        scaffoldBackgroundColor: const Color(0xFF121212),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00ADB5),
          secondary: Color(0xFF7952B3),
          surface: Color(0xFF1E1E1E),
        ),
      ),
      home: const ChatScreen(),
    );
  }
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  // URLs de conexión predefinidas (Tailscale es la alternativa recomendada a Cloudflare)
  static const String defaultTailscaleUrl = 'http://100.64.0.1:8000/ask';
  static const String defaultLanUrl = 'http://10.21.209.217:8000/ask';
  static const String defaultTunnelUrl = 'https://deutsch-quote-dubai-signed.trycloudflare.com/ask';

  final TextEditingController _urlController = TextEditingController(text: defaultTailscaleUrl);
  final TextEditingController _messageController = TextEditingController();
  
  // Historial visual de mensajes en pantalla
  final List<Map<String, String>> _messages = [
    {
      'sender': 'Nem', 
      'text': 'Hola, soy Nem. Lista para colaborar con Nemotron 3 Ultra y soporte offline local.'
    }
  ];
  
  // Historial estructurado para enviar al backend
  final List<Map<String, String>> _conversationHistory = [];

  // Estado del modelo activo:
  // null o 'nemotron-3-ultra' = IA principal online
  // 'gpt-oss:120b' = IA especializada en código / deep research
  // 'Llama-3.2-1B-Instruct-Q4_K_M' = IA local offline
  String? _activeModel;

  // Estado de modo offline forzado por el usuario
  bool _isOfflineMode = false;

  bool _isLoading = false;
  bool _isListeningBackground = false;
  
  late stt.SpeechToText _speech;
  FlutterTts? _flutterTts;

  @override
  void initState() {
    super.initState();
    _speech = stt.SpeechToText();
    if (Platform.isAndroid || Platform.isIOS) {
      _flutterTts = FlutterTts();
    }
    _initAudioEngine();
  }

  Future<void> _initAudioEngine() async {
    if (_flutterTts != null) {
      await _flutterTts!.setLanguage("es-MX");
      await _flutterTts!.setPitch(1.0);
      await _flutterTts!.setSpeechRate(0.5);
    }

    try {
      bool available = await _speech.initialize(
        onError: (val) => debugPrint('STT Error: $val'),
        onStatus: (val) {
          if (val == 'done' && _isListeningBackground) {
            _startPassiveListening();
          }
        },
      );
      if (available) {
        _toggleWakeWordListening();
      }
    } catch (e) {
      debugPrint("Speech recognition error: $e");
    }
  }

  void _clearContext({bool userTriggered = false}) {
    setState(() {
      _conversationHistory.clear();
      _activeModel = null;
      _messages.add({
        'sender': 'Nem',
        'text': '🔄 *Contexto borrado.* He vuelto al modo estándar con Nemotron 3 Ultra.'
      });
    });
    if (userTriggered) {
      _speak("Contexto reiniciado.");
    }
  }

  void _toggleOfflineMode() {
    setState(() {
      _isOfflineMode = !_isOfflineMode;
      if (_isOfflineMode) {
        _activeModel = 'Llama Local (Offline)';
        _messages.add({
          'sender': 'Nem',
          'text': '📴 *Modo Offline activado.* Usando modelo local de la tablet (llama.cpp) sin conexión a internet.'
        });
        _speak("Modo offline activado.");
      } else {
        _activeModel = null;
        _messages.add({
          'sender': 'Nem',
          'text': '🌐 *Modo Online activado.* Conectado a Nemotron 3 Ultra en la nube.'
        });
        _speak("Modo online activado.");
      }
    });
  }

  void _toggleWakeWordListening() {
    setState(() {
      _isListeningBackground = !_isListeningBackground;
    });

    if (_isListeningBackground) {
      _startPassiveListening();
    } else {
      _speech.stop();
    }
  }

  void _startPassiveListening() {
    if (!_isListeningBackground) return;

    _speech.listen(
      onResult: (val) {
        String recognized = val.recognizedWords.toLowerCase();
        
        if (recognized.contains('limpiar chat') || recognized.contains('nuevo chat')) {
          _speech.stop();
          _clearContext(userTriggered: true);
          return;
        }

        if (recognized.contains('gracias nem') || recognized.contains('gracias')) {
          _speech.stop();
          _closeSession();
          return;
        }

        if (recognized.contains('modo offline') || recognized.contains('modo local')) {
          _speech.stop();
          if (!_isOfflineMode) _toggleOfflineMode();
          return;
        }

        if (recognized.contains('modo online') || recognized.contains('activar nube')) {
          _speech.stop();
          if (_isOfflineMode) _toggleOfflineMode();
          return;
        }

        if (recognized.contains('nem')) {
          _speech.stop();
          _speak("Dime, te escucho.");
          
          String cleanPrompt = recognized.replaceAll('nem', '').trim();
          if (cleanPrompt.isNotEmpty) {
            _messageController.text = cleanPrompt;
            _sendMessage();
          } else {
            _listenForUserPrompt();
          }
        }
      },
      listenFor: const Duration(seconds: 10),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      localeId: "es_MX",
    );
  }

  void _listenForUserPrompt() {
    _speech.listen(
      onResult: (val) {
        if (val.finalResult) {
          _messageController.text = val.recognizedWords;
          _sendMessage();
        }
      },
      listenFor: const Duration(seconds: 10),
      pauseFor: const Duration(seconds: 3),
      localeId: "es_MX",
    );
  }

  Future<void> _closeSession() async {
    setState(() {
      _messages.add({'sender': 'Tú', 'text': 'Gracias Nem'});
      _messages.add({
        'sender': 'Nem',
        'text': '¡De nada! He cerrado la sesión temática. Vuelvo a Nemotron para tus consultas habituales.'
      });
      _conversationHistory.clear();
      _activeModel = null;
    });
    await _speak("De nada, vuelvo a Nemotron.");
  }

  Future<void> _speak(String text) async {
    String spokenText = text;
    if (text.contains("```") || text.contains("def ") || text.length > 300) {
      spokenText = "Listo, revisa el resultado en pantalla.";
    }

    if (Platform.isAndroid || Platform.isIOS) {
      try {
        if (_flutterTts != null) {
          await _flutterTts!.speak(spokenText);
        }
      } catch (e) {
        debugPrint("TTS Mobile error: $e");
      }
    } else if (Platform.isLinux) {
      try {
        await Process.run('sh', [
          '-c',
          'echo "$spokenText" | ./piper/piper --model voices/es_MX-claude-high.onnx --output_file output.wav && aplay output.wav > /dev/null 2>&1'
        ]);
      } catch (e) {
        debugPrint("TTS Linux error: $e");
      }
    }
  }

  Future<void> _sendMessage() async {
    final prompt = _messageController.text.trim();
    if (prompt.isEmpty) return;

    final lowerPrompt = prompt.toLowerCase();

    // Detección manual o por voz de comando de cierre temático
    if (lowerPrompt.contains('gracias nem') || lowerPrompt == 'gracias' || lowerPrompt == 'listo nem') {
      _messageController.clear();
      await _closeSession();
      return;
    }

    if (lowerPrompt == 'nuevo chat' || lowerPrompt == 'limpiar') {
      _messageController.clear();
      _clearContext(userTriggered: true);
      return;
    }

    // Comandos rápidos de offline/online por texto
    if (lowerPrompt == 'modo offline' || lowerPrompt == 'offline') {
      _messageController.clear();
      if (!_isOfflineMode) _toggleOfflineMode();
      return;
    }
    if (lowerPrompt == 'modo online' || lowerPrompt == 'online') {
      _messageController.clear();
      if (_isOfflineMode) _toggleOfflineMode();
      return;
    }

    // Si detecta 'investiga' o 'busca profunda', marca la intención especializada
    if (!_isOfflineMode && (_activeModel == null || _activeModel == 'nemotron-3-ultra') &&
        (lowerPrompt.startsWith('investiga') || lowerPrompt.startsWith('busca profunda') || lowerPrompt.contains('codigo') || lowerPrompt.contains('programa'))) {
      _activeModel = 'gpt-oss:120b';
    }

    setState(() {
      _messages.add({'sender': 'Tú', 'text': prompt});
      _isLoading = true;
    });
    _messageController.clear();

    _conversationHistory.add({'role': 'user', 'content': prompt});

    try {
      final response = await http.post(
        Uri.parse(_urlController.text.trim()),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'prompt': prompt,
          'history': _conversationHistory,
          'active_model': _activeModel,
          'offline': _isOfflineMode,
        }),
      ).timeout(const Duration(seconds: 90));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final reply = data['response'] ?? 'Respuesta vacía';
        final newActiveModel = data['active_model'] as String?;
        final isSessionClosed = data['session_closed'] == true;

        _conversationHistory.add({'role': 'assistant', 'content': reply});

        setState(() {
          _messages.add({'sender': 'Nem', 'text': reply});
          if (isSessionClosed) {
            _activeModel = null;
          } else if (newActiveModel != null && !_isOfflineMode) {
            _activeModel = newActiveModel;
          }
        });
        await _speak(reply);
      } else {
        final err = 'Error del servidor: HTTP ${response.statusCode}';
        setState(() {
          _messages.add({'sender': 'Nem', 'text': err});
        });
        await _speak(err);
      }
    } catch (e) {
      final err = 'Error de conexión ($e). Pasando temporalmente a modo offline local.';
      setState(() {
        _messages.add({'sender': 'Nem', 'text': err});
      });
      await _speak('Error de conexión con el servidor.');
    } finally {
      setState(() {
        _isLoading = false;
      });
      if (_isListeningBackground) {
        _startPassiveListening();
      }
    }
  }

  void _showConnectionDialog() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E1E1E),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Seleccionar Método de Conexión',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 8),
              const Text(
                'Elige cómo conectarte al servidor de la tablet/PC sin depender exclusivamente de Cloudflare.',
                style: TextStyle(fontSize: 13, color: Colors.grey),
              ),
              const SizedBox(height: 16),
              ListTile(
                leading: const Icon(Icons.vpn_lock, color: Colors.tealAccent),
                title: const Text('Tailscale VPN (Recomendado)'),
                subtitle: const Text('IP fija privada, sin puertos abiertos ni caducidad'),
                trailing: const Icon(Icons.arrow_forward_ios, size: 14),
                onTap: () {
                  setState(() => _urlController.text = defaultTailscaleUrl);
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.wifi, color: Colors.blueAccent),
                title: const Text('Red Local WiFi (LAN)'),
                subtitle: const Text('Conexión directa por IP local (10.21.209.217:8000)'),
                trailing: const Icon(Icons.arrow_forward_ios, size: 14),
                onTap: () {
                  setState(() => _urlController.text = defaultLanUrl);
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.cloud_queue, color: Colors.purpleAccent),
                title: const Text('Cloudflare Tunnel'),
                subtitle: const Text('Túnel público HTTPS (trycloudflare.com)'),
                trailing: const Icon(Icons.arrow_forward_ios, size: 14),
                onTap: () {
                  setState(() => _urlController.text = defaultTunnelUrl);
                  Navigator.pop(context);
                },
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    // Determinar badge visual del modelo actual
    String modelBadgeText = 'Nemotron 3 Ultra';
    Color modelBadgeColor = Colors.teal.shade800;

    if (_isOfflineMode) {
      modelBadgeText = '📴 Llama Local (Offline)';
      modelBadgeColor = Colors.orange.shade900;
    } else if (_activeModel == 'gpt-oss:120b') {
      modelBadgeText = '⚡ gpt-oss:120b (Especializada)';
      modelBadgeColor = Colors.purple.shade800;
    } else if (_activeModel == 'gemma4:31b') {
      modelBadgeText = '👁️ gemma4:31b (Visión)';
      modelBadgeColor = Colors.indigo.shade800;
    }

    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Nem AI'),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: modelBadgeColor,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                modelBadgeText,
                style: const TextStyle(fontSize: 11, color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        centerTitle: true,
        backgroundColor: Colors.black26,
        actions: [
          // Botón selector de modo offline / online
          IconButton(
            icon: Icon(
              _isOfflineMode ? Icons.cloud_off : Icons.cloud_done,
              color: _isOfflineMode ? Colors.orangeAccent : Colors.tealAccent,
            ),
            tooltip: _isOfflineMode ? 'Modo Offline (Click para Online)' : 'Modo Online (Click para Offline)',
            onPressed: _toggleOfflineMode,
          ),
          // Botón limpiar chat / cerrar contexto
          IconButton(
            icon: const Icon(Icons.delete_sweep, color: Colors.amberAccent),
            tooltip: 'Nuevo Chat / Limpiar Contexto ("gracias nem")',
            onPressed: () => _clearContext(userTriggered: true),
          ),
          // Botón micrófono background
          IconButton(
            icon: Icon(
              _isListeningBackground ? Icons.mic : Icons.mic_off,
              color: _isListeningBackground ? Colors.greenAccent : Colors.redAccent,
            ),
            tooltip: _isListeningBackground ? 'Escucha pasiva activada ("Nem")' : 'Escucha desactivada',
            onPressed: _toggleWakeWordListening,
          ),
        ],
      ),
      body: Column(
        children: [
          // Barra de dirección de conexión con acceso rápido a opciones
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 6.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _urlController,
                    decoration: InputDecoration(
                      labelText: 'Dirección del Servidor (Backend)',
                      prefixIcon: const Icon(Icons.link),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      filled: true,
                      fillColor: Colors.grey.shade900,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filledTonal(
                  icon: const Icon(Icons.alt_route),
                  tooltip: 'Opciones de conexión (Tailscale, LAN, Cloudflare)',
                  onPressed: _showConnectionDialog,
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 5.0),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                final isUser = msg['sender'] == 'Tú';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 6.0),
                    padding: const EdgeInsets.all(14.0),
                    constraints: BoxConstraints(
                      maxWidth: MediaQuery.of(context).size.width * 0.85,
                    ),
                    decoration: BoxDecoration(
                      color: isUser ? const Color(0xFF00ADB5) : const Color(0xFF1E1E1E),
                      borderRadius: BorderRadius.circular(12.0),
                      border: isUser ? null : Border.all(color: Colors.white12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          msg['sender']!,
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: isUser ? Colors.white : const Color(0xFF00ADB5),
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 4),
                        isUser
                            ? Text(
                                msg['text']!,
                                style: const TextStyle(color: Colors.white, fontSize: 15),
                              )
                            : MarkdownBody(
                                data: msg['text']!,
                                selectable: true,
                                styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
                                  p: const TextStyle(color: Colors.white, fontSize: 14, height: 1.4),
                                  code: TextStyle(
                                    backgroundColor: Colors.black45,
                                    color: Colors.greenAccent.shade100,
                                    fontFamily: 'monospace',
                                  ),
                                  codeblockDecoration: BoxDecoration(
                                    color: Colors.black54,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                ),
                              ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          if (_isLoading) const LinearProgressIndicator(color: Color(0xFF00ADB5)),
          Padding(
            padding: const EdgeInsets.all(10.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: _isOfflineMode ? 'Escribe a Nem (Modo Offline Local)...' : 'Escribe a Nem (Nemotron 3 Ultra)...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(25),
                      ),
                      filled: true,
                      fillColor: Colors.grey.shade900,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),
                FloatingActionButton.small(
                  onPressed: _isLoading ? null : _sendMessage,
                  backgroundColor: const Color(0xFF00ADB5),
                  child: const Icon(Icons.send, color: Colors.white),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}