import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/dashboard/farmer_home_screen.dart';
import '../../features/insect_ai/insect_ai_screen.dart';
import '../../features/plant_sound/plant_sound_screen.dart';
import '../../features/plant_disease/plant_disease_screen.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/signup_screen.dart';
import '../../core/providers/auth_provider.dart';

class AppRouter {
  static GoRouter createRouter(WidgetRef ref) {
    return GoRouter(
      initialLocation: '/login',
      redirect: (context, state) async {
        final authState = ref.read(authProvider);
        final isAuthRoute = state.matchedLocation == '/login' ||
            state.matchedLocation == '/signup';

        // If not authenticated and not on auth route, redirect to login
        if (!authState.isAuthenticated && !isAuthRoute) {
          return '/login';
        }

        // If authenticated and on auth route, redirect to home
        if (authState.isAuthenticated && isAuthRoute) {
          return '/home';
        }

        return null;
      },
      routes: [
        GoRoute(
          path: '/login',
          builder: (context, state) => const LoginScreen(),
        ),
        GoRoute(
          path: '/signup',
          builder: (context, state) => const SignupScreen(),
        ),
        GoRoute(
          path: '/home',
          builder: (context, state) => const FarmerHomeScreen(),
        ),
        GoRoute(
          path: '/',
          builder: (context, state) => const FarmerHomeScreen(),
        ),
        GoRoute(
          path: '/insect-ai',
          builder: (context, state) => const InsectAiScreen(),
        ),
        GoRoute(
          path: '/plant-sound',
          builder: (context, state) => const PlantSoundScreen(),
        ),
        GoRoute(
          path: '/plant-disease',
          builder: (context, state) => const PlantDiseaseScreen(),
        ),
      ],
    );
  }
}
