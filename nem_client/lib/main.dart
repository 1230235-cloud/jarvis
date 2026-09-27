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
  final TextEditingController _urlController = TextEditingController(
    text: 'https://deutsch-quote-dubai-signed.trycloudflare.com/ask',
  );
  final TextEditingController _messageController = TextEditingController();
  
  // Historial visual de mensajes en pantalla
  final List<Map<String, String>> _messages = [
    {'sender': 'Nem', 'text': 'Hola, soy Nem. Lista para colaborar.'}
  ];
  
  // Historial estructurado para enviar al backend
  final List<Map<String, String>> _conversationHistory = [];

  // Estado del modelo activo (null = router general)
  String? _activeModel;

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
        'text': '🔄 *Contexto borrado.* He vuelto al modo estándar.'
      });
    });
    if (userTriggered) {
      _speak("Contexto reiniciado.");
    }
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
        'text': '¡De nada! He cerrado la sesión temática. Quedo atenta para tu siguiente consulta.'
      });
      _conversationHistory.clear();
      _activeModel = null;
    });
    await _speak("De nada, quedo atenta.");
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

    // Detección manual o por voz de comando de cierre
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

    // Si detecta 'investiga' o 'busca profunda', activa el modelo especializado en el backend
    if (_activeModel == null && (lowerPrompt.startsWith('investiga') || lowerPrompt.startsWith('busca profunda'))) {
      _activeModel = 'deep_research';
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
          'model_override': _activeModel,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final reply = data['response'] ?? 'Respuesta vacía';
        
        _conversationHistory.add({'role': 'assistant', 'content': reply});

        setState(() {
          _messages.add({'sender': 'Nem', 'text': reply});
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
      final err = 'Error de conexión: $e';
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Nem AI Client'),
            if (_activeModel != null) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.purple.shade800,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  _activeModel!,
                  style: const TextStyle(fontSize: 11, color: Colors.white),
                ),
              ),
            ]
          ],
        ),
        centerTitle: true,
        backgroundColor: Colors.black26,
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_sweep, color: Colors.orangeAccent),
            tooltip: 'Nuevo Chat / Limpiar Contexto',
            onPressed: () => _clearContext(userTriggered: true),
          ),
          IconButton(
            icon: Icon(
              _isListeningBackground ? Icons.mic : Icons.mic_off,
              color: _isListeningBackground ? Colors.greenAccent : Colors.redAccent,
            ),
            tooltip: _isListeningBackground ? 'Escucha pasiva activada' : 'Escucha desactivada',
            onPressed: _toggleWakeWordListening,
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(10.0),
            child: TextField(
              controller: _urlController,
              decoration: InputDecoration(
                labelText: 'Túnel URL',
                prefixIcon: const Icon(Icons.link),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                filled: true,
                fillColor: Colors.grey.shade900,
              ),
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
                      color: isUser ? Colors.blueAccent.shade700 : const Color(0xFF1E1E1E),
                      borderRadius: BorderRadius.circular(12.0),
                      border: isUser ? null : Border.all(color: Colors.white10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          msg['sender']!,
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: isUser ? Colors.white : Colors.blueAccent,
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
          if (_isLoading) const LinearProgressIndicator(),
          Padding(
            padding: const EdgeInsets.all(10.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: 'Escribe a Nem...',
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
                  backgroundColor: Colors.blueAccent,
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