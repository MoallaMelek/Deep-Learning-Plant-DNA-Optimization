import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';

class ApiService {
  static String get _baseUrl {
    const configured = String.fromEnvironment('API_BASE_URL');
    if (configured.isNotEmpty) return configured;
    if (kIsWeb) return 'http://127.0.0.1:8000';
    return 'http://172.20.10.4:8000';
  }

  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  final Dio _dio = Dio(BaseOptions(
    baseUrl: _baseUrl,
    connectTimeout: const Duration(seconds: 5),
    receiveTimeout: const Duration(seconds: 15),
    headers: {'Content-Type': 'application/json'},
  ));

  Future<MultipartFile> _multipartFromXFile(
    XFile file,
    String filename,
  ) async {
    if (kIsWeb) {
      return MultipartFile.fromBytes(
        await file.readAsBytes(),
        filename: filename,
      );
    }
    return MultipartFile.fromFile(file.path, filename: filename);
  }

  // ─── Plant Disease (Wheat CNN) ────────────────────────────────────────────
  Future<Map<String, dynamic>> analyzePlantDisease(XFile imageFile) async {
    final formData = FormData.fromMap({
      'image': await _multipartFromXFile(imageFile, 'plant.jpg'),
    });
    final resp = await _dio.post('/wheat/predict', data: formData);
    return resp.data as Map<String, dynamic>;
  }

  // ─── Insect AI — Sound ────────────────────────────────────────────────────
  Future<Map<String, dynamic>> analyzeInsectSound(XFile audioFile) async {
    final formData = FormData.fromMap({
      'audio': await _multipartFromXFile(audioFile, 'insect.wav'),
    });
    final resp = await _dio.post('/sound/predict', data: formData);
    final data = resp.data as Map<String, dynamic>;
    final rawConf = data['confidence'];
    final conf = rawConf is num ? (rawConf > 1 ? rawConf / 100 : rawConf) : 0.0;
    return {
      'species':
          data['predicted_class'] ?? data['prediction'] ?? data['species'],
      'confidence': conf,
      'top_predictions': data['top_predictions'],
    };
  }

  // ─── Insect AI — Image ────────────────────────────────────────────────────
  Future<Map<String, dynamic>> analyzeInsectImage(XFile imageFile) async {
    final formData = FormData.fromMap({
      'file': await _multipartFromXFile(imageFile, 'insect.jpg'),
    });
    final resp = await _dio.post('/pest/predict', data: formData);
    final data = resp.data as Map<String, dynamic>;
    final top1 = (data['top1'] is Map) ? data['top1'] as Map : const {};
    return {
      'species': top1['class_name'] ?? data['prediction'] ?? data['species'],
      'confidence': top1['confidence'] ?? data['confidence'] ?? 0.0,
      'top5': data['top5'],
    };
  }

  // ─── IoT Plant Sound / Smart Irrigation ──────────────────────────────────
  Future<List<dynamic>> getIoTPlants() async {
    final resp = await _dio.get('/cropdna/api/iot/plants');
    final data = resp.data as List<dynamic>;
    return data.map((item) {
      final plant = Map<String, dynamic>.from(item as Map);
      plant['status'] = plant['status'] ?? plant['stress_type'] ?? 'HEALTHY';
      plant['temp'] = plant['temp'] ?? plant['temperature'] ?? 0.0;
      plant['name'] ??= plant['plant_id'] ?? plant['id'];
      return plant;
    }).toList();
  }

  Future<List<dynamic>> getPlantHistory(String plantId) async {
    final resp = await _dio.get('/cropdna/api/iot/plants/$plantId/history');
    return resp.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> getIoTStats() async {
    final resp = await _dio.get('/cropdna/api/iot/dashboard/stats');
    return resp.data as Map<String, dynamic>;
  }
}
