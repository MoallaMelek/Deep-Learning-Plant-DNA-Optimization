import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/services/tts_service.dart';
import '../../widgets/agri_agent.dart';
import '../../widgets/tts_button.dart';
import '../../core/providers/auth_provider.dart';

class _FeatureCard {
  final String titleAr;
  final String descAr;
  final IconData icon;
  final List<Color> gradient;
  final String route;
  final String ttsText;

  const _FeatureCard({
    required this.titleAr,
    required this.descAr,
    required this.icon,
    required this.gradient,
    required this.route,
    required this.ttsText,
  });
}

const List<_FeatureCard> _cards = [
  _FeatureCard(
    titleAr: 'عالم الحشرات',
    descAr: 'اكتشف نوع الحشرة بالصوت أو بالصورة وحمي محصولك',
    icon: Icons.pest_control_rounded,
    gradient: [AppColors.cardGreenLight, AppColors.cardGreenMedium],
    route: '/insect-ai',
    ttsText:
        'عالم الحشرات. اكتشف نوع الحشرة بالصوت أو بالصورة وحمي محصولك من الأضرار.',
  ),
  _FeatureCard(
    titleAr: 'صوت النبات',
    descAr: 'ري ذكي تلقائي — شاهد حالة نباتاتك في الوقت الحقيقي',
    icon: Icons.waves_rounded,
    gradient: [AppColors.cardGreenMedium, AppColors.cardGreenLight],
    route: '/plant-sound',
    ttsText:
        'صوت النبات. نظام ري ذكي تلقائي. شاهد حالة نباتاتك ومستوى الماء في الوقت الحقيقي.',
  ),
  _FeatureCard(
    titleAr: 'صحة النبات',
    descAr: 'صوّر ورق النبتة واعرف إذا كان هناك مرض باستعمال الذكاء الاصطناعي',
    icon: Icons.local_florist_rounded,
    gradient: [AppColors.cardGreenDark, AppColors.cardGreenMedium],
    route: '/plant-disease',
    ttsText:
        'صحة النبات. صوّر ورق النبتة واعرف إذا كان هناك مرض باستعمال الذكاء الاصطناعي.',
  ),
];

class FarmerHomeScreen extends ConsumerStatefulWidget {
  const FarmerHomeScreen({super.key});

  @override
  ConsumerState<FarmerHomeScreen> createState() => _FarmerHomeScreenState();
}

class _FarmerHomeScreenState extends ConsumerState<FarmerHomeScreen> {
  @override
  void initState() {
    super.initState();
    // Welcome message on open
    Future.delayed(const Duration(milliseconds: 800), () {
      final authState = ref.read(authProvider);
      final userName = authState.user?['full_name'] ?? 'فلاح';
      TtsService()
          .speak('مرحبا يا $userName في AgriCulture. اختر الخدمة التي تحب.');
    });
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final userName = authState.user?['full_name'] ?? 'فلاح';

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        children: [
          // Background gradient blobs
          _BackgroundBlobs(),

          SafeArea(
            child: Column(
              children: [
                // ── Header ────────────────────────────────────────────────
                _Header(),
                const SizedBox(height: 8),

                // ── Welcome Text ──────────────────────────────────────────
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            'أهلا يا $userName 👋',
                            style: GoogleFonts.cairo(
                              fontSize: 26,
                              fontWeight: FontWeight.w900,
                              color: AppColors.textHeading,
                              height: 1.2,
                            ),
                          )
                              .animate()
                              .fadeIn(duration: 600.ms, curve: Curves.easeOut)
                              .slideY(begin: -20, end: 0, duration: 600.ms),
                          const SizedBox(width: 12),
                          TtsButton(
                            text:
                                'أهلا بك يا $userName في منصة الفلاحة الذكية. اختر الخدمة التي تحب.',
                          ).animate().fadeIn(duration: 700.ms),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Container(
                        margin: const EdgeInsets.only(top: 8),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 6),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [
                              AppColors.cardGreenLight.withOpacity(0.1),
                              AppColors.cardGreenMedium.withOpacity(0.05),
                            ],
                          ),
                          borderRadius: BorderRadius.circular(22),
                          border: Border.all(
                            color: AppColors.cardGreenMedium.withOpacity(0.2),
                            width: 1,
                          ),
                        ),
                        child: Text(
                          'اختر الخدمة التي تحتاجها',
                          style: GoogleFonts.cairo(
                            fontSize: 13,
                            color: AppColors.cardGreenDark,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      )
                          .animate()
                          .fadeIn(duration: 800.ms, curve: Curves.easeOut)
                          .slideY(begin: 10, end: 0, duration: 600.ms),
                    ],
                  ),
                ),

                const SizedBox(height: 32),

                // ── Feature Cards ─────────────────────────────────────────
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: ListView.separated(
                      itemCount: _cards.length,
                      physics: const BouncingScrollPhysics(),
                      separatorBuilder: (_, __) => const SizedBox(height: 16),
                      itemBuilder: (context, i) {
                        return _FeatureCardWidget(
                          card: _cards[i],
                          index: i,
                        );
                      },
                    ),
                  ),
                ),

                const SizedBox(height: 90), // space for agent FAB
              ],
            ),
          ),

          // ── AgriAgent Floating ─────────────────────────────────────────
          const Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: AgriAgent(screenContext: 'home'),
          ),
        ],
      ),
    );
  }
}

// ─── Background animated blobs ────────────────────────────────────────────────
class _BackgroundBlobs extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Top-right blob
        Positioned(
          top: -100,
          right: -100,
          child: Container(
            width: 320,
            height: 320,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  AppColors.cardGreenLight.withOpacity(0.15),
                  AppColors.cardGreenMedium.withOpacity(0.05),
                  Colors.transparent,
                ],
                stops: const [0.0, 0.6, 1.0],
              ),
            ),
          ).animate(onPlay: (c) => c.repeat(reverse: true)).scale(
                begin: const Offset(1, 1),
                end: const Offset(1.2, 1.2),
                duration: 6.seconds,
                curve: Curves.easeInOut,
              ),
        ),
        // Bottom-left blob
        Positioned(
          bottom: 80,
          left: -80,
          child: Container(
            width: 260,
            height: 260,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  AppColors.cardGreenDark.withOpacity(0.12),
                  AppColors.cardGreenMedium.withOpacity(0.04),
                  Colors.transparent,
                ],
                stops: const [0.0, 0.5, 1.0],
              ),
            ),
          ).animate(onPlay: (c) => c.repeat(reverse: true)).scale(
                begin: const Offset(1, 1),
                end: const Offset(1.3, 1.3),
                duration: 8.seconds,
                curve: Curves.easeInOut,
              ),
        ),
        // Dot grid overlay
        Positioned.fill(
          child: CustomPaint(painter: _DotGridPainter()),
        ),
        // Additional accent blob
        Positioned(
          top: 200,
          left: -50,
          child: Container(
            width: 150,
            height: 150,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primary.withOpacity(0.04),
            ),
          ).animate(onPlay: (c) => c.repeat(reverse: true)).fade(
                begin: 0.3,
                end: 0.7,
                duration: 3.seconds,
              ),
        ),
      ],
    );
  }
}

class _DotGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.primary.withOpacity(0.04)
      ..strokeWidth = 1.5;
    const spacing = 32.0;
    for (double x = 0; x < size.width; x += spacing) {
      for (double y = 0; y < size.height; y += spacing) {
        canvas.drawCircle(Offset(x, y), 1.5, paint);
      }
    }
  }

  @override
  bool shouldRepaint(_) => false;
}

// ─── Header ───────────────────────────────────────────────────────────────────
class _Header extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        children: [
          // Logo container with gradient
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  AppColors.cardGreenLight,
                  AppColors.cardGreenMedium,
                ],
              ),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: AppColors.cardGreenMedium.withOpacity(0.3),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(
              Icons.eco_rounded,
              color: Colors.white,
              size: 28,
            ),
          ).animate().scale(duration: 400.ms, curve: Curves.elasticOut),
          const SizedBox(width: 14),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'AgriCulture',
                style: GoogleFonts.cairo(
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                  color: AppColors.textHeading,
                  letterSpacing: -0.5,
                  height: 1.0,
                ),
              ),
              Container(
                height: 2.5,
                width: 110,
                margin: const EdgeInsets.only(top: 2),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(2),
                  gradient: const LinearGradient(
                    colors: [
                      AppColors.cardGreenLight,
                      AppColors.cardGreenMedium
                    ],
                  ),
                ),
              ),
            ],
          ),
          const Spacer(),
          // Live indicator
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.cardGreenLight.withOpacity(0.15),
                  AppColors.cardGreenMedium.withOpacity(0.08),
                ],
              ),
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: AppColors.cardGreenMedium.withOpacity(0.3),
                width: 1.2,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.cardGreenMedium,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.cardGreenMedium.withOpacity(0.5),
                        blurRadius: 6,
                      ),
                    ],
                  ),
                )
                    .animate(onPlay: (c) => c.repeat())
                    .fadeIn(duration: 600.ms)
                    .then()
                    .fadeOut(duration: 600.ms),
                const SizedBox(width: 7),
                Text(
                  'نشيط',
                  style: GoogleFonts.cairo(
                    color: AppColors.cardGreenDark,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          // Logout button
          GestureDetector(
            onTap: () async {
              await ref.read(authProvider.notifier).logout();
              if (context.mounted) {
                context.go('/login');
              }
            },
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppColors.backgroundAlt,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: AppColors.glassBorder,
                  width: 1.2,
                ),
              ),
              child: const Icon(
                Icons.logout_rounded,
                color: AppColors.cardGreenDark,
                size: 22,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Feature Card Widget ──────────────────────────────────────────────────────
class _FeatureCardWidget extends StatefulWidget {
  const _FeatureCardWidget({required this.card, required this.index});
  final _FeatureCard card;
  final int index;

  @override
  State<_FeatureCardWidget> createState() => _FeatureCardWidgetState();
}

class _FeatureCardWidgetState extends State<_FeatureCardWidget> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final card = widget.card;

    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        context.push(card.route);
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.96 : 1.0,
        duration: const Duration(milliseconds: 120),
        child: Container(
          height: 150,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: card.gradient,
            ),
            borderRadius: BorderRadius.circular(28),
            boxShadow: [
              BoxShadow(
                color: card.gradient[1].withOpacity(0.35),
                blurRadius: 24,
                offset: const Offset(0, 10),
                spreadRadius: -4,
              ),
              BoxShadow(
                color: Colors.black.withOpacity(0.08),
                blurRadius: 8,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(28),
            child: Stack(
              children: [
                // Glass shimmer overlay
                Positioned(
                  top: -40,
                  right: -40,
                  child: Container(
                    width: 140,
                    height: 140,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Colors.white.withOpacity(0.12),
                    ),
                  ),
                ),
                Positioned(
                  bottom: -30,
                  left: -30,
                  child: Container(
                    width: 100,
                    height: 100,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Colors.white.withOpacity(0.06),
                    ),
                  ),
                ),
                // Content
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Row(
                    children: [
                      // Icon circle with glass effect
                      Container(
                        width: 64,
                        height: 64,
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              Colors.white.withOpacity(0.35),
                              Colors.white.withOpacity(0.1),
                            ],
                          ),
                          borderRadius: BorderRadius.circular(22),
                          border: Border.all(
                            color: Colors.white.withOpacity(0.4),
                            width: 1.5,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.1),
                              blurRadius: 8,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Icon(card.icon, color: Colors.white, size: 32),
                      ),
                      const SizedBox(width: 16),
                      // Title + desc
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              card.titleAr,
                              style: GoogleFonts.cairo(
                                fontSize: 20,
                                fontWeight: FontWeight.w900,
                                color: Colors.white,
                                shadows: [
                                  Shadow(
                                    color: Colors.black.withOpacity(0.15),
                                    blurRadius: 8,
                                    offset: const Offset(0, 2),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              card.descAr,
                              style: GoogleFonts.cairo(
                                fontSize: 12,
                                color: Colors.white.withOpacity(0.9),
                                height: 1.5,
                                fontWeight: FontWeight.w500,
                              ),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 10),
                      // Right side: TTS + arrow
                      Column(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          TtsButton(
                            text: card.ttsText,
                            size: 40,
                            color: Colors.white.withOpacity(0.9),
                          ),
                          Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  Colors.white.withOpacity(0.35),
                                  Colors.white.withOpacity(0.15),
                                ],
                              ),
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: Colors.white.withOpacity(0.4),
                                width: 1.2,
                              ),
                            ),
                            child: const Icon(
                              Icons.arrow_back_ios_new_rounded,
                              color: Colors.white,
                              size: 16,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        )
            .animate()
            .fadeIn(
                delay: (widget.index * 150).ms,
                duration: 600.ms,
                curve: Curves.easeOutCubic)
            .slideY(
                begin: 0.35,
                end: 0,
                duration: 600.ms,
                curve: Curves.easeOutCubic),
      ),
    );
  }
}
