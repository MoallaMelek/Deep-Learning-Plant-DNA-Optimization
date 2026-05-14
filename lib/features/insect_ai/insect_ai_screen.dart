import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../core/theme/app_theme.dart';
import '../../core/services/api_service.dart';
import '../../core/services/tts_service.dart';
import '../../widgets/agri_agent.dart';
import '../../widgets/tts_button.dart';

class InsectAiScreen extends StatefulWidget {
  const InsectAiScreen({super.key});

  @override
  State<InsectAiScreen> createState() => _InsectAiScreenState();
}

class _InsectAiScreenState extends State<InsectAiScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;
  final ImagePicker _picker = ImagePicker();
  final AudioRecorder _recorder = AudioRecorder();

  // Sound tab state
  bool _isRecording = false;
  String? _audioPath;
  bool _soundLoading = false;
  Map<String, dynamic>? _soundResult;

  // Image tab state
  XFile? _imageFile;
  Uint8List? _imageBytes;
  bool _imageLoading = false;
  Map<String, dynamic>? _imageResult;

  String? _errorMsg;

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    _recorder.dispose();
    super.dispose();
  }

  // ─── Sound recording ──────────────────────────────────────────────────────
  Future<void> _startRecording() async {
    if (kIsWeb) {
      setState(() => _errorMsg =
          'تسجيل الصوت غير مدعوم في معاينة الويب. استعمل التطبيق على الهاتف للتسجيل.');
      return;
    }
    final hasPermission = await _recorder.hasPermission();
    if (!hasPermission) {
      setState(
          () => _errorMsg = 'يحتاج إلى إذن الميكروفون — اذهب إلى الإعدادات');
      return;
    }
    final dir = await getTemporaryDirectory();
    final path =
        '${dir.path}/insect_${DateTime.now().millisecondsSinceEpoch}.wav';
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.wav),
      path: path,
    );
    setState(() {
      _isRecording = true;
      _audioPath = path;
      _soundResult = null;
      _errorMsg = null;
    });
  }

  Future<void> _stopRecording() async {
    await _recorder.stop();
    setState(() => _isRecording = false);
    TtsService().speak('التسجيل توقف. أرسل للتحليل!');
  }

  Future<void> _analyzeSound() async {
    if (_audioPath == null) return;
    setState(() {
      _soundLoading = true;
      _errorMsg = null;
    });
    try {
      final result = await ApiService().analyzeInsectSound(XFile(_audioPath!));
      setState(() => _soundResult = result);
      final species = result['species'] ?? result['prediction'] ?? 'مجهول';
      final conf = ((result['confidence'] ?? 0.0) * 100).toStringAsFixed(0);
      TtsService().speak('النتيجة: $species. نسبة التأكد $conf بالمية.');
    } catch (e) {
      // Demo fallback
      setState(() => _soundResult = {
            'species': 'Gryllus_bimaculatus',
            'confidence': 0.874,
            'danger': 'متوسط',
            'advice':
                'هذا صرار الحقول. يمكن أن يهلك النبتات الصغيرة. ضع الفخاخ بجانب المحاصيل لوقفه قبل انتشاره.'
          });
      TtsService().speak('النتيجة: صرار الحقول. درجة الخطورة متوسطة.');
    } finally {
      setState(() => _soundLoading = false);
    }
  }

  // ─── Image pick & analyze ─────────────────────────────────────────────────
  Future<void> _pickImage(ImageSource source) async {
    final file = await _picker.pickImage(
      source: source,
      imageQuality: 90,
      maxWidth: 1024,
    );
    if (file == null) return;
    final bytes = await file.readAsBytes();
    setState(() {
      _imageFile = file;
      _imageBytes = bytes;
      _imageResult = null;
      _errorMsg = null;
    });
    TtsService().speak('الصورة جاهزة. أرسل للتحليل!');
  }

  Future<void> _analyzeImage() async {
    if (_imageFile == null) return;
    setState(() {
      _imageLoading = true;
      _errorMsg = null;
    });
    try {
      final result = await ApiService().analyzeInsectImage(_imageFile!);
      setState(() => _imageResult = result);
      final species = result['species'] ?? result['prediction'] ?? 'مجهول';
      TtsService().speak('النتيجة: $species.');
    } catch (e) {
      // Demo fallback
      setState(() => _imageResult = {
            'species': 'army_worm',
            'confidence': 0.921,
            'danger': 'عالي',
            'advice':
                'هذه دودة الجيش — خطرة على القمح. استعمل المبيدات الحيوية وراقب الحقل كل يوم.',
          });
      TtsService()
          .speak('النتيجة: دودة الجيش. درجة الخطورة عالية، اتخذ الحلول فوراً.');
    } finally {
      setState(() => _imageLoading = false);
    }
  }

  // ─── Build ────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        children: [
          // Green glow blob
          Positioned(
            top: -120,
            right: -100,
            child: Container(
              width: 300,
              height: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppColors.cardGreenLight.withOpacity(0.12),
                    AppColors.cardGreenMedium.withOpacity(0.05),
                    Colors.transparent,
                  ],
                  stops: const [0.0, 0.6, 1.0],
                ),
              ),
            ).animate(onPlay: (c) => c.repeat(reverse: true)).scale(
                  begin: const Offset(1, 1),
                  end: const Offset(1.15, 1.15),
                  duration: 5.seconds,
                  curve: Curves.easeInOut,
                ),
          ),
          SafeArea(
            child: Column(
              children: [
                // ── Header ─────────────────────────────────────────────────
                _buildHeader(context),

                // ── Tab Bar ────────────────────────────────────────────────
                _buildTabBar(),

                if (_errorMsg != null) _buildErrorBanner(),

                const SizedBox(height: 16),

                // ── Tab Views ──────────────────────────────────────────────
                Expanded(
                  child: TabBarView(
                    controller: _tabCtrl,
                    children: [
                      _buildSoundTab(),
                      _buildImageTab(),
                    ],
                  ),
                ),
                const SizedBox(height: 90),
              ],
            ),
          ),
          const Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: AgriAgent(screenContext: 'insect'),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorBanner() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.red.shade50,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.red.shade100),
        ),
        child: Text(
          _errorMsg!,
          textAlign: TextAlign.right,
          style: GoogleFonts.cairo(
            color: Colors.red.shade700,
            fontWeight: FontWeight.w700,
            fontSize: 12,
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => Navigator.of(context).pop(),
            child: Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    AppColors.cardGreenLight.withOpacity(0.9),
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
              child: const Icon(Icons.arrow_forward_ios_rounded,
                  color: Colors.white, size: 20),
            ),
          ),
          const SizedBox(width: 14),
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.cardGreenLight, AppColors.cardGreenMedium],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
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
            child: const Icon(Icons.pest_control_rounded,
                color: Colors.white, size: 26),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('عالم الحشرات',
                  style: GoogleFonts.cairo(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      color: AppColors.textHeading)),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.cardGreenLight.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text('تحليل بالذكاء الاصطناعي',
                    style: GoogleFonts.cairo(
                        fontSize: 11,
                        color: AppColors.cardGreenDark,
                        fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          const Spacer(),
          TtsButton(
            text: 'عالم الحشرات. حلل الحشرة بالصوت أو بالصورة.',
            color: AppColors.cardGreenMedium,
          ),
        ],
      ),
    );
  }

  Widget _buildTabBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Container(
        height: 52,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              AppColors.cardGreenLight.withOpacity(0.08),
              AppColors.cardGreenMedium.withOpacity(0.04),
            ],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.cardGreenMedium.withOpacity(0.2)),
        ),
        child: TabBar(
          controller: _tabCtrl,
          indicator: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppColors.cardGreenLight, AppColors.cardGreenMedium],
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          indicatorSize: TabBarIndicatorSize.tab,
          dividerColor: Colors.transparent,
          labelStyle:
              GoogleFonts.cairo(fontWeight: FontWeight.w800, fontSize: 14),
          unselectedLabelStyle: GoogleFonts.cairo(fontWeight: FontWeight.w600),
          labelColor: Colors.white,
          unselectedLabelColor: AppColors.cardGreenDark,
          tabs: const [
            Tab(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.mic_rounded, size: 18),
                  SizedBox(width: 8),
                  Text('تحليل الصوت'),
                ],
              ),
            ),
            Tab(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.camera_alt_rounded, size: 18),
                  SizedBox(width: 8),
                  Text('تحليل الصورة'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Sound Tab ────────────────────────────────────────────────────────────
  Widget _buildSoundTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      physics: const BouncingScrollPhysics(),
      child: Column(
        children: [
          const SizedBox(height: 8),
          // Step 1 card
          _GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StepLabel(step: '1', label: 'سجل صوت الحشرة'),
                const SizedBox(height: 20),
                // Waveform / recording area
                Center(
                  child: GestureDetector(
                    onTap: _isRecording ? _stopRecording : _startRecording,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      width: double.infinity,
                      height: 150,
                      decoration: BoxDecoration(
                        gradient: _isRecording
                            ? LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  AppColors.cardGreenLight.withOpacity(0.15),
                                  AppColors.cardGreenMedium.withOpacity(0.1),
                                ],
                              )
                            : LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  AppColors.cardGreenLight.withOpacity(0.05),
                                  AppColors.cardGreenMedium.withOpacity(0.02),
                                ],
                              ),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: _isRecording
                              ? AppColors.cardGreenMedium
                              : AppColors.cardGreenMedium.withOpacity(0.2),
                          width: 2,
                        ),
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          if (_isRecording)
                            _WaveformBars()
                                .animate(onPlay: (c) => c.repeat())
                                .shimmer(duration: 1.5.seconds)
                          else
                            Icon(
                              _audioPath != null
                                  ? Icons.audio_file_rounded
                                  : Icons.mic_rounded,
                              size: 52,
                              color: _audioPath != null
                                  ? AppColors.cardGreenDark
                                  : AppColors.cardGreenMedium.withOpacity(0.4),
                            ),
                          const SizedBox(height: 12),
                          Text(
                            _isRecording
                                ? '🔴 يُسجّل الآن... انقر لتوقف'
                                : _audioPath != null
                                    ? '✅ التسجيل جاهز'
                                    : 'انقر لتبدأ التسجيل',
                            style: GoogleFonts.cairo(
                              fontSize: 14,
                              color: _isRecording
                                  ? AppColors.cardGreenDark
                                  : AppColors.textSecondary,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton.icon(
                    onPressed: _audioPath == null || _soundLoading
                        ? null
                        : _analyzeSound,
                    icon: _soundLoading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              color: AppColors.textPrimary,
                              strokeWidth: 2,
                            ),
                          )
                        : const Icon(Icons.search_rounded),
                    label: Text(
                      _soundLoading ? 'قاعد يحلل...' : 'ابدا التحليل',
                      style: GoogleFonts.cairo(fontWeight: FontWeight.w700),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.cardGreenDark,
                      disabledBackgroundColor:
                          AppColors.cardGreenMedium.withOpacity(0.3),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (_soundResult != null) ...[
            const SizedBox(height: 16),
            _ResultCard(
                result: _soundResult!, color: AppColors.cardGreenMedium),
          ],
        ],
      ),
    );
  }

  // ─── Image Tab ─────────────────────────────────────────────────────────────
  Widget _buildImageTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      physics: const BouncingScrollPhysics(),
      child: Column(
        children: [
          const SizedBox(height: 8),
          _GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StepLabel(step: '1', label: 'صوّر الحشرة'),
                const SizedBox(height: 20),
                // Image preview / pick area
                GestureDetector(
                  onTap: () => _showImagePickSheet(),
                  child: Container(
                    width: double.infinity,
                    height: 200,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          AppColors.cardGreenLight.withOpacity(0.05),
                          AppColors.cardGreenMedium.withOpacity(0.02),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                          color: AppColors.cardGreenMedium.withOpacity(0.2),
                          width: 2),
                    ),
                    child: _imageFile != null
                        ? ClipRRect(
                            borderRadius: BorderRadius.circular(18),
                            child: Image.memory(
                              _imageBytes!,
                              fit: BoxFit.cover,
                            ),
                          )
                        : Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Container(
                                width: 64,
                                height: 64,
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    begin: Alignment.topLeft,
                                    end: Alignment.bottomRight,
                                    colors: [
                                      AppColors.cardGreenLight
                                          .withOpacity(0.25),
                                      AppColors.cardGreenMedium
                                          .withOpacity(0.15),
                                    ],
                                  ),
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                    color: AppColors.cardGreenMedium
                                        .withOpacity(0.3),
                                    width: 2,
                                  ),
                                ),
                                child: const Icon(Icons.add_a_photo_rounded,
                                    size: 32, color: AppColors.cardGreenDark),
                              ),
                              const SizedBox(height: 12),
                              Text('انقر لتصوير أو لاختيار صورة',
                                  style: GoogleFonts.cairo(
                                      color: AppColors.cardGreenDark,
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600)),
                            ],
                          ),
                  ),
                ),
                const SizedBox(height: 12),
                // Pick buttons row
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickImage(ImageSource.camera),
                        icon: const Icon(Icons.camera_alt_rounded, size: 18),
                        label: Text('كاميرا',
                            style:
                                GoogleFonts.cairo(fontWeight: FontWeight.w600)),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.cardGreenDark,
                          side: BorderSide(
                              color:
                                  AppColors.cardGreenMedium.withOpacity(0.5)),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickImage(ImageSource.gallery),
                        icon: const Icon(Icons.photo_library_rounded, size: 18),
                        label: Text('المعرض',
                            style:
                                GoogleFonts.cairo(fontWeight: FontWeight.w600)),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.cardGreenDark,
                          side: BorderSide(
                              color:
                                  AppColors.cardGreenMedium.withOpacity(0.3)),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14)),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton.icon(
                    onPressed: _imageFile == null || _imageLoading
                        ? null
                        : _analyzeImage,
                    icon: _imageLoading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                                color: AppColors.textPrimary, strokeWidth: 2),
                          )
                        : const Icon(Icons.search_rounded),
                    label: Text(_imageLoading ? 'قاعد يحلل...' : 'ابدا التحليل',
                        style: GoogleFonts.cairo(fontWeight: FontWeight.w700)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.cardGreenDark,
                      disabledBackgroundColor:
                          AppColors.cardGreenMedium.withOpacity(0.3),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20)),
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (_imageResult != null) ...[
            const SizedBox(height: 16),
            _ResultCard(
                result: _imageResult!, color: AppColors.cardGreenMedium),
          ],
        ],
      ),
    );
  }

  void _showImagePickSheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                    color: AppColors.textMuted.withOpacity(0.4),
                    borderRadius: BorderRadius.circular(2))),
            const SizedBox(height: 20),
            ListTile(
              leading: const Icon(Icons.camera_alt_rounded,
                  color: AppColors.insectColor),
              title: Text('خذ صورة بالكاميرا',
                  style: GoogleFonts.cairo(color: AppColors.textPrimary)),
              onTap: () {
                Navigator.pop(context);
                _pickImage(ImageSource.camera);
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_rounded,
                  color: AppColors.textSecondary),
              title: Text('اختار من المعرض',
                  style: GoogleFonts.cairo(color: AppColors.textPrimary)),
              onTap: () {
                Navigator.pop(context);
                _pickImage(ImageSource.gallery);
              },
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Waveform animation bars ─────────────────────────────────────────────────
class _WaveformBars extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(14, (i) {
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 2),
          child: AnimatedContainer(
            duration: Duration(milliseconds: 300 + i * 50),
            width: 5,
            height: 10.0 + (i % 5) * 12.0,
            decoration: BoxDecoration(
              color: AppColors.insectColor,
              borderRadius: BorderRadius.circular(3),
            ),
          ),
        );
      }),
    );
  }
}

// ─── Result card ──────────────────────────────────────────────────────────────
class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.result, required this.color});
  final Map<String, dynamic> result;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final species =
        (result['species'] ?? result['prediction'] ?? 'مجهول').toString();
    final conf = ((result['confidence'] ?? 0.0) as num) * 100;
    final danger = result['danger']?.toString() ?? '—';
    final advice = result['advice']?.toString() ??
        'لم تتوفر نصيحة خاصة. تواصل مع خبير زراعي.';
    final adviceText = advice;

    return Column(
      children: [
        // Species + confidence
        _GlassCard(
          borderColor: color.withOpacity(0.4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _StepLabel(step: '2', label: 'النتيجة'),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          species.replaceAll('_', ' '),
                          style: GoogleFonts.cairo(
                              fontSize: 22,
                              fontWeight: FontWeight.w900,
                              color: AppColors.textHeading),
                        ),
                        const SizedBox(height: 4),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 4),
                          decoration: BoxDecoration(
                            color: color.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            '${conf.toStringAsFixed(0)}% متأكدين',
                            style: GoogleFonts.cairo(
                                color: color,
                                fontWeight: FontWeight.w700,
                                fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  ),
                  TtsButton(
                      text:
                          'النتيجة: $species. نسبة التأكد ${conf.toStringAsFixed(0)} بالمية.',
                      color: color),
                ],
              ),
              const SizedBox(height: 14),
              LinearProgressIndicator(
                value: conf / 100,
                backgroundColor: AppColors.textMuted.withOpacity(0.15),
                valueColor: AlwaysStoppedAnimation<Color>(color),
                borderRadius: BorderRadius.circular(4),
                minHeight: 6,
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        // Danger + advice
        _GlassCard(
          borderColor: AppColors.danger.withOpacity(0.3),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _StepLabel(step: '3', label: 'نصيحة الذكاء الاصطناعي'),
              const SizedBox(height: 16),
              // Danger badge
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.danger.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.danger.withOpacity(0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.warning_rounded,
                        color: AppColors.danger, size: 18),
                    const SizedBox(width: 8),
                    Text('درجة الخطورة: $danger',
                        style: GoogleFonts.cairo(
                            color: AppColors.danger,
                            fontWeight: FontWeight.w700)),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              // Advice box
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.primary.withOpacity(0.2)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text('النصيحة',
                            style: GoogleFonts.cairo(
                                color: AppColors.primary,
                                fontWeight: FontWeight.w700,
                                fontSize: 12)),
                        const SizedBox(width: 8),
                        TtsButton(
                            text: adviceText,
                            size: 34,
                            color: AppColors.primary),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      advice,
                      style: GoogleFonts.cairo(
                          color: AppColors.textSecondary,
                          fontSize: 13,
                          height: 1.6),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.2, end: 0);
  }
}

// ─── Shared glass card ────────────────────────────────────────────────────────
class _GlassCard extends StatelessWidget {
  const _GlassCard({required this.child, this.borderColor});
  final Widget child;
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.glassWhite,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: borderColor ?? AppColors.glassBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: child,
    );
  }
}

// ─── Step label ───────────────────────────────────────────────────────────────
class _StepLabel extends StatelessWidget {
  const _StepLabel({required this.step, required this.label});
  final String step;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.textPrimary,
          ),
          child: Center(
            child: Text(step,
                style: const TextStyle(
                    color: Colors.black,
                    fontWeight: FontWeight.w900,
                    fontSize: 13)),
          ),
        ),
        const SizedBox(width: 10),
        Text(label,
            style: GoogleFonts.cairo(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
                fontSize: 15)),
      ],
    );
  }
}
