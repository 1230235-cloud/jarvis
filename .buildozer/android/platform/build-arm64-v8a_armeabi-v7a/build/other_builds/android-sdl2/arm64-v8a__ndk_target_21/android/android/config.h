#define BOOTSTRAP "sdl2"
#define IS_SDL2 1
#define IS_SDL3 0
#define PY2 0
#define ANDROID_LIBS_DIR "/run/media/jinsoon005/juegos1/jarvis/jarvis/.buildozer/android/platform/build-arm64-v8a_armeabi-v7a/build/libs_collections/jarvis/arm64-v8a:/run/media/jinsoon005/juegos1/jarvis/jarvis/.buildozer/android/platform/build-arm64-v8a_armeabi-v7a/build/bootstrap_builds/sdl2/obj/local/arm64-v8a"
#define JAVA_NAMESPACE "org.kivy.android"
#define JNI_NAMESPACE "org/kivy/android"
#define ACTIVITY_CLASS_NAME "org.kivy.android.PythonActivity"
#define ACTIVITY_CLASS_NAMESPACE "org/kivy/android/PythonActivity"
#define SERVICE_CLASS_NAME "org.kivy.android.PythonService"
JNIEnv *SDL_AndroidGetJNIEnv(void);
#define SDL_ANDROID_GetJNIEnv SDL_AndroidGetJNIEnv
