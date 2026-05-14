import 'package:flutter_tts/flutter_tts.dart';
import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';

class TtsService {
  static final TtsService _instance = TtsService._internal();
  factory TtsService() => _instance;
  TtsService._internal();

  final FlutterTts _tts = FlutterTts();
  final AudioPlayer _audioPlayer = AudioPlayer();
  bool _initialized = false;
  bool _hasLocalArabicVoice = false;

  static const String _preferredLocale = 'ar-TN';
  static const List<String> _fallbackLocales = [
    'ar-TN',
    'ar-TN',
    'ar',
    'ar-SA',
    'ar-EG',
    'ar-DZ',
    'ar-MA',
  ];

  Future<String?> _pickLocale() async {
    // List all available languages for debugging
    try {
      final languages = await _tts.getLanguages;
      debugPrint('TTS: Available languages: $languages');
    } catch (e) {
      debugPrint('TTS: Error getting languages: $e');
    }

    for (final locale in _fallbackLocales) {
      final available = await _tts.isLanguageAvailable(locale);
      debugPrint('TTS: Checking locale $locale: available=$available');
      if (available == true) {
        debugPrint('TTS: Found available locale: $locale');
        return locale;
      }
    }
    debugPrint('TTS: No Arabic locale found on device');
    return null;
  }

  Future<void> _selectVoice(String locale) async {
    try {
      final voices = await _tts.getVoices;
      if (voices is! List) return;
      final List<Map<dynamic, dynamic>> casted = voices
          .whereType<Map>()
          .map((v) => Map<dynamic, dynamic>.from(v))
          .toList();

      debugPrint('TTS: Available voices: $casted');

      // Try exact match first
      var match = casted.firstWhere(
        (v) => v['locale']?.toString() == locale,
        orElse: () => const {},
      );

      // If no exact match, try to find any Arabic voice
      if (match.isEmpty) {
        match = casted.firstWhere(
          (v) => v['locale']?.toString().startsWith('ar') == true,
          orElse: () => const {},
        );
      }

      if (match.isNotEmpty) {
        debugPrint(
            'TTS: Selected voice: ${match['name']} (${match['locale']})');
        await _tts.setVoice({
          'name': match['name'],
          'locale': match['locale'],
        });
      } else {
        debugPrint('TTS: No Arabic voice found, will use default voice');
      }
    } catch (e) {
      debugPrint('TTS: Voice selection error: $e');
    }
  }

  Future<void> _init() async {
    if (_initialized) return;

    final locale = await _pickLocale();
    final languageToSet = locale ?? _preferredLocale;

    debugPrint('TTS: Setting language to: $languageToSet');
    await _tts.setLanguage(languageToSet);

    if (locale != null) {
      await _selectVoice(locale);
    }

    await _tts.setSpeechRate(0.85);
    await _tts.setVolume(1.0);
    await _tts.setPitch(1.0);

    _hasLocalArabicVoice = locale != null;
    _initialized = true;
    debugPrint(
        'TTS: Initialization complete (local Arabic: $_hasLocalArabicVoice)');
  }

  Future<void> _speakWithWebTts(String text) async {
    try {
      debugPrint('TTS: Using backend proxy TTS for: $text');
      final encodedText = Uri.encodeComponent(text);
      // Call the backend TTS proxy endpoint
      const configured = String.fromEnvironment('API_BASE_URL');
      final apiBaseUrl = configured.isNotEmpty
          ? configured
          : (kIsWeb ? 'http://127.0.0.1:8000' : 'http://172.20.10.4:8000');
      final backendUrl = '$apiBaseUrl/tts';
      final url = '$backendUrl?text=$encodedText';

      await _audioPlayer.setUrl(url);
      await _audioPlayer.play();
      debugPrint('TTS: Backend proxy TTS playback started');
    } catch (e) {
      debugPrint('TTS: Backend proxy TTS exception: $e');
    }
  }

  Future<void> speak(String text) async {
    await _init();
    await stop();
    debugPrint('TTS: Speaking: $text (local Arabic: $_hasLocalArabicVoice)');

    if (_hasLocalArabicVoice || kIsWeb) {
      await _tts.speak(text);
    } else {
      await _speakWithWebTts(text);
    }
  }

  Future<void> stop() async {
    await _tts.stop();
    await _audioPlayer.stop();
  }
}
