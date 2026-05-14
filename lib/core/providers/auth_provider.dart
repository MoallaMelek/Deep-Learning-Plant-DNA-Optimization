import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/auth_service.dart';

class AuthState {
  final bool isLoading;
  final bool isAuthenticated;
  final Map<String, dynamic>? user;
  final String? error;

  AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.user,
    this.error,
  });

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    Map<String, dynamic>? user,
    String? error,
    bool clearError = false,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      user: user ?? this.user,
      error: clearError ? null : error ?? this.error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService = AuthService();

  AuthNotifier() : super(AuthState()) {
    _checkAuthStatus();
  }

  Future<void> _checkAuthStatus() async {
    final isAuth = await _authService.isAuthenticated();
    if (isAuth) {
      final user = await _authService.getUser();
      state = state.copyWith(
        isAuthenticated: true,
        user: user,
      );
    }
  }

  Future<void> signup({
    required String email,
    required String phone,
    required String password,
    required String fullName,
    String? farmName,
    String? location,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);

    final result = await _authService.signup(
      email: email,
      phone: phone,
      password: password,
      fullName: fullName,
      farmName: farmName,
      location: location,
    );

    if (result['success'] == true) {
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        user: result['user'] as Map<String, dynamic>,
        clearError: true,
      );
    } else {
      state = state.copyWith(
        isLoading: false,
        error: result['error'] as String,
      );
    }
  }

  Future<void> login({
    required String identifier,
    required String password,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);

    final result = await _authService.login(
      identifier: identifier,
      password: password,
    );

    if (result['success'] == true) {
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        user: result['user'] as Map<String, dynamic>,
        clearError: true,
      );
    } else {
      state = state.copyWith(
        isLoading: false,
        error: result['error'] as String,
      );
    }
  }

  Future<void> logout() async {
    await _authService.logout();
    state = AuthState();
  }

  void clearError() {
    state = state.copyWith(clearError: true);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});
