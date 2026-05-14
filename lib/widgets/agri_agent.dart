import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../core/services/tts_service.dart';
import '../core/theme/app_theme.dart';

/// Floating AI assistant that explains each feature to the farmer in Tunisian Arabic.
/// Must be placed inside a [Stack] with `Positioned(bottom:0, left:0, right:0)`.
class AgriAgent extends StatefulWidget {
  const AgriAgent({super.key, this.screenContext = 'home'});

  final String screenContext;

  @override
  State<AgriAgent> createState() => _AgriAgentState();
}

class _AgriAgentState extends State<AgriAgent>
    with SingleTickerProviderStateMixin {
  bool _isOpen = false;
  late AnimationController _pulseCtrl;
  late Animation<double> _pulseAnim;

  static const Map<String, Map<String, String>> _messages = {
    'home': {
      'title': 'مرحبا! أنا مساعدك الذكي 🌱',
      'msg':
          'ماذا تريد أن تفعل اليوم؟\n\n🐛 عالم الحشرات — تعرّف على الحشرة بصوتها أو بصورتها\n\n🌊 صوت النبات — شاهد كيف يسقي النبات تلقائيا\n\n🌿 صحة النبات — أرسل صورة واعرف إذا كان هناك مرض\n\nانقر على البطاقة لتبدأ!',
    },
    'insect': {
      'title': 'عالم الحشرات 🐛',
      'msg':
          'هذا النظام يعرف أكثر من 20 نوعا من الحشرات.\n\n1️⃣ أرسل تسجيلا صوتيا للحشرة — الذكاء الاصطناعي يحلله\n2️⃣ أو صوّر الحشرة بالكاميرا\n3️⃣ تعرّف على درجة الخطورة والحل\n\nاستخدم الميكروفون أو الكاميرا وابدأ!',
    },
    'sound': {
      'title': 'صوت النبات 🌊',
      'msg':
          'هذا النظام يسمع النباتات بالأمواج فوق الصوتية!\n\n✅ كل نبتة لها حساس — تقيس رطوبة التربة\n✅ عندما تجف — يسقي وحده تلقائيا\n✅ توفير المياه يصل 30%\n\nشاهد حالة كل نبتة في الوقت الحقيقي!',
    },
    'disease': {
      'title': 'صحة النبات 🌿',
      'msg':
          'نظام ذكي يكشف أمراض النباتات بالصورة!\n\n📸 صوّر ورق النبتة\n🔍 الذكاء الاصطناعي يحلل الصورة\n📋 ستعرف المرض ونسبة التأكد\n\nالنتيجة تظهر في ثوانٍ — بدون خبير!',
    },
  };

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _pulseAnim = Tween<double>(begin: 1.0, end: 1.12).animate(
      CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    super.dispose();
  }

  void _toggle() {
    setState(() => _isOpen = !_isOpen);
    if (_isOpen) {
      final ctx = widget.screenContext;
      TtsService().speak(_messages[ctx]?['msg'] ?? '');
    } else {
      TtsService().stop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final ctx = widget.screenContext;
    final title = _messages[ctx]?['title'] ?? 'مساعدك الذكي';
    final msg = _messages[ctx]?['msg'] ?? '';

    // Use a Column so the widget has a natural size.
    // The chat bubble appears above the FAB using an Overlay-style approach.
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // ── Chat bubble (conditionally shown above the FAB) ──────────────
        if (_isOpen)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Material(
              color: Colors.transparent,
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withOpacity(0.25),
                      blurRadius: 20,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Header row
                    Row(
                      children: [
                        Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.2),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.eco_rounded,
                              color: Colors.white, size: 20),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            title,
                            style: GoogleFonts.cairo(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                              fontSize: 14,
                            ),
                          ),
                        ),
                        GestureDetector(
                          onTap: () {
                            TtsService().stop();
                            TtsService().speak(msg);
                          },
                          child: Container(
                            width: 32,
                            height: 32,
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.15),
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(Icons.volume_up_rounded,
                                color: Colors.white, size: 16),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Text(
                      msg,
                      style: GoogleFonts.cairo(
                        color: Colors.white.withOpacity(0.95),
                        fontSize: 13,
                        height: 1.7,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Align(
                      alignment: Alignment.centerRight,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 5),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          'خبير الذكاء الاصطناعي 🤖',
                          style: GoogleFonts.cairo(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),

        // ── FAB button ────────────────────────────────────────────────────
        Padding(
          padding: const EdgeInsets.only(bottom: 28),
          child: ScaleTransition(
            scale: _isOpen ? const AlwaysStoppedAnimation(1.0) : _pulseAnim,
            child: GestureDetector(
              onTap: _toggle,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: _isOpen
                        ? [
                            AppColors.danger,
                            AppColors.danger.withOpacity(0.8),
                          ]
                        : [AppColors.primary, AppColors.primaryDark],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: (_isOpen ? AppColors.danger : AppColors.primary)
                          .withOpacity(0.45),
                      blurRadius: 20,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: Icon(
                  _isOpen ? Icons.close_rounded : Icons.smart_toy_rounded,
                  color: Colors.white,
                  size: 30,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
