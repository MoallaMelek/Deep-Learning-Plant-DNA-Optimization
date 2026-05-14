import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  static String get _baseUrl {
    const configured = String.fromEnvironment('API_BASE_URL');
    if (configured.isNotEmpty) return configured;
    if (kIsWeb) return 'http://127.0.0.1:8000';
    return 'http://172.20.10.4:8000';
  }

  final Dio _dio = Dio(BaseOptions(
    baseUrl: _baseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 30),
    headers: {'Content-Type': 'application/json'},
  ));

  static const String _tokenKey = 'auth_token';
  static const String _userKey = 'auth_user';

  String _friendlyDioError(DioException e, String fallback) {
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return 'لا يمكن الاتصال بالخادم. تأكد أن backend يعمل على $_baseUrl';
    }
    final data = e.response?.data;
    if (data is Map && data['detail'] != null) {
      return data['detail'].toString();
    }
    return e.message ?? fallback;
  }

  Future<Map<String, dynamic>> signup({
    required String email,
    required String phone,
    required String password,
    required String fullName,
    String? farmName,
    String? location,
  }) async {
    try {
      final response = await _dio.post('/auth/signup', data: {
        'email': email,
        'phone': phone,
        'password': password,
        'full_name': fullName,
        'farm_name': farmName,
        'location': location,
      });

      final data = response.data as Map<String, dynamic>;
      final token = data['access_token'] as String;
      final user = data['user'] as Map<String, dynamic>;

      // Save token and user
      await _saveToken(token);
      await _saveUser(user);

      return {'success': true, 'user': user, 'token': token};
    } on DioException catch (e) {
      final message = _friendlyDioError(e, 'Signup failed');
      return {'success': false, 'error': message};
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>> login({
    required String identifier,
    required String password,
  }) async {
    try {
      final response = await _dio.post('/auth/login', data: {
        'identifier': identifier,
        'password': password,
      });

      final data = response.data as Map<String, dynamic>;
      final token = data['access_token'] as String;
      final user = data['user'] as Map<String, dynamic>;

      // Save token and user
      await _saveToken(token);
      await _saveUser(user);

      return {'success': true, 'user': user, 'token': token};
    } on DioException catch (e) {
      final message = _friendlyDioError(e, 'Login failed');
      return {'success': false, 'error': message};
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>?> getCurrentUser() async {
    final token = await getToken();
    if (token == null) return null;

    try {
      final response = await _dio.get(
        '/auth/me',
        queryParameters: {'token': token},
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      return null;
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_userKey);
  }

  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  Future<Map<String, dynamic>?> getUser() async {
    final prefs = await SharedPreferences.getInstance();
    final userJson = prefs.getString(_userKey);
    if (userJson == null) return null;
    return jsonDecode(userJson) as Map<String, dynamic>;
  }

  Future<bool> isAuthenticated() async {
    final token = await getToken();
    return token != null && token.isNotEmpty;
  }

  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  Future<void> _saveUser(Map<String, dynamic> user) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userKey, jsonEncode(user));
  }
}
