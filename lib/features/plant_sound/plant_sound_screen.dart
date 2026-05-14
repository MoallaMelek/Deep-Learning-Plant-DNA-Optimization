import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../core/theme/app_theme.dart';
import '../../core/services/api_service.dart';
import '../../core/services/tts_service.dart';
import '../../widgets/agri_agent.dart';
import '../../widgets/tts_button.dart';

class PlantSoundScreen extends StatefulWidget {
  const PlantSoundScreen({super.key});

  @override
  State<PlantSoundScreen> createState() => _PlantSoundScreenState();
}

class _PlantSoundScreenState extends State<PlantSoundScreen> {
  List<Map<String, dynamic>> _plants = [];
  String? _selectedPlantId;
  bool _loading = true;
  Timer? _pollTimer;

  // Demo plant data if backend is offline
  static const List<Map<String, dynamic>> _demoPlants = [
    {
      'id': 'P1',
      'name': 'قمح ألفا',
      'status': 'HEALTHY',
      'vwc': 35.5,
      'temp': 22.4,
      'humidity': 45.0,
    },
    {
      'id': 'P2',
      'name': 'شعير بيتا',
      'status': 'HEALTHY',
      'vwc': 38.2,
      'temp': 21.8,
      'humidity': 48.2,
    },
    {
      'id': 'P3',
      'name': 'قمح دلتا',
      'status': 'DRY',
      'vwc': 12.4,
      'temp': 25.6,
      'humidity': 30.5,
    },
  ];

  @override
  void initState() {
    super.initState();
    // Show demo data immediately for instant feedback
    _plants = _demoPlants.map((e) => Map<String, dynamic>.from(e)).toList();
    _selectedPlantId = 'P1';
    _loading = false;

    // Then fetch real data in background
    _fetchPlants();
    _pollTimer =
        Timer.periodic(const Duration(seconds: 10), (_) => _fetchPlants());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchPlants() async {
    try {
      final data = await ApiService().getIoTPlants();
      if (mounted) {
        setState(() {
          _plants = data
              .map<Map<String, dynamic>>(
                  (e) => Map<String, dynamic>.from(e as Map))
              .toList();
          if (_plants.isNotEmpty) {
            _selectedPlantId = _plants[0]['id'] ?? _plants[0]['plant_id'];
          }
          _loading = false;
        });
        _checkAlerts();
      }
    } catch (_) {
      // Keep showing demo data if API fails - no state change needed
    }
  }

  void _checkAlerts() {
    for (final p in _plants) {
      final status = p['status']?.toString().toUpperCase() ?? '';
      final action = p['action']?.toString().toUpperCase() ?? '';
      if (status == 'DRY' || action == 'IRRIGATE_NOW') {
        final name = p['name'] ?? p['plant_id'] ?? 'النبتة';
        TtsService().speak('تنبيه! $name تحتاج ماء. السبالة تحلت وحدها.');
        break;
      }
    }
  }

  Map<String, dynamic>? get _selectedPlant {
    if (_selectedPlantId == null) return null;
    try {
      return _plants.firstWhere(
        (p) => (p['id'] ?? p['plant_id'])?.toString() == _selectedPlantId,
      );
    } catch (_) {
      return _plants.isNotEmpty ? _plants[0] : null;
    }
  }

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
                _buildHeader(context),
                Expanded(
                  child: _loading
                      ? const Center(
                          child: CircularProgressIndicator(
                              color: AppColors.primary))
                      : RefreshIndicator(
                          color: AppColors.primary,
                          backgroundColor: AppColors.surface,
                          onRefresh: _fetchPlants,
                          child: SingleChildScrollView(
                            physics: const AlwaysScrollableScrollPhysics(
                              parent: BouncingScrollPhysics(),
                            ),
                            padding: const EdgeInsets.fromLTRB(20, 16, 20, 100),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _buildStatsRow(),
                                const SizedBox(height: 24),
                                _buildSectionTitle('حالة النباتات الآن'),
                                const SizedBox(height: 14),
                                _buildPlantCards(),
                                const SizedBox(height: 24),
                                if (_selectedPlant != null) ...[
                                  _buildSectionTitle('تفاصيل النبتة المختارة'),
                                  const SizedBox(height: 14),
                                  _buildPlantDetail(_selectedPlant!),
                                ],
                              ],
                            ),
                          ),
                        ),
                ),
              ],
            ),
          ),
          const Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: AgriAgent(screenContext: 'sound'),
          ),
        ],
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
            child:
                const Icon(Icons.waves_rounded, color: Colors.white, size: 26),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('صوت النبات',
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
                child: Text('ري ذكي تلقائي — IoT',
                    style: GoogleFonts.cairo(
                        fontSize: 11,
                        color: AppColors.cardGreenDark,
                        fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          const Spacer(),
          TtsButton(
            text: 'صوت النبات. نظام ري ذكي تلقائي.',
            color: AppColors.cardGreenMedium,
          ),
        ],
      ),
    );
  }

  Widget _buildStatsRow() {
    final dryCount = _plants
        .where((p) => (p['status'] ?? '').toString().toUpperCase() == 'DRY')
        .length;
    final healthyCount = _plants.length - dryCount;

    return Row(
      children: [
        Expanded(
          child: _StatChip(
            icon: Icons.water_drop_rounded,
            label: '$healthyCount نبتة سليمة',
            color: AppColors.cardGreenMedium,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _StatChip(
            icon: Icons.warning_amber_rounded,
            label: '$dryCount تحتاج ماء',
            color: dryCount > 0 ? AppColors.danger : AppColors.textMuted,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _StatChip(
            icon: Icons.sensors_rounded,
            label: '${_plants.length} حساسات',
            color: AppColors.cardGreenLight,
          ),
        ),
      ],
    );
  }

  Widget _buildSectionTitle(String title) {
    return Row(
      children: [
        Text(
          title,
          style: GoogleFonts.cairo(
            fontSize: 16,
            fontWeight: FontWeight.w800,
            color: AppColors.textHeading,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Container(
            height: 1,
            color: AppColors.textMuted.withOpacity(0.15),
          ),
        ),
        const SizedBox(width: 10),
        TtsButton(text: title, size: 32),
      ],
    );
  }

  Widget _buildPlantCards() {
    return SizedBox(
      height: 180,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _plants.length,
        separatorBuilder: (_, __) => const SizedBox(width: 12),
        itemBuilder: (context, i) {
          final plant = _plants[i];
          final id = (plant['id'] ?? plant['plant_id'] ?? '').toString();
          final isSelected = id == _selectedPlantId;
          final status = (plant['status'] ?? '').toString().toUpperCase();
          final isDry = status == 'DRY';

          return GestureDetector(
            onTap: () {
              setState(() => _selectedPlantId = id);
              final name = plant['name'] ?? id;
              TtsService().speak('اخترت $name. '
                  '${isDry ? "هذه النبتة تحتاج ماء!" : "النبتة بصحة."}');
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 250),
              width: 148,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: isSelected
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
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color: isSelected
                      ? AppColors.cardGreenMedium
                      : isDry
                          ? AppColors.danger.withOpacity(0.5)
                          : AppColors.cardGreenMedium.withOpacity(0.2),
                  width: isSelected ? 2 : 1.5,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: isDry
                              ? AppColors.danger.withOpacity(0.15)
                              : AppColors.cardGreenLight.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Icon(
                          isDry
                              ? Icons.warning_rounded
                              : Icons.local_florist_rounded,
                          color: isDry
                              ? AppColors.danger
                              : AppColors.cardGreenDark,
                          size: 20,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: isDry
                              ? AppColors.danger.withOpacity(0.12)
                              : AppColors.cardGreenLight.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          isDry ? 'جافة' : 'سليمة',
                          style: GoogleFonts.cairo(
                            color: isDry
                                ? AppColors.danger
                                : AppColors.cardGreenDark,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    plant['name']?.toString() ?? id,
                    style: GoogleFonts.cairo(
                      color: AppColors.textHeading,
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const Spacer(),
                  // VWC bar
                  _MiniSensorRow(
                    label: 'رطوبة',
                    value: '${(plant['vwc'] ?? 0).toStringAsFixed(1)}%',
                    icon: Icons.water_drop_outlined,
                    color: AppColors.info,
                  ),
                  const SizedBox(height: 4),
                  _MiniSensorRow(
                    label: 'حرارة',
                    value: '${(plant['temp'] ?? 0).toStringAsFixed(1)}°',
                    icon: Icons.thermostat_rounded,
                    color: AppColors.warning,
                  ),
                ],
              ),
            )
                .animate()
                .fadeIn(delay: (i * 80).ms, duration: 400.ms)
                .slideX(begin: 0.1, end: 0),
          );
        },
      ),
    );
  }

  Widget _buildPlantDetail(Map<String, dynamic> plant) {
    final status = (plant['status'] ?? '').toString().toUpperCase();
    final isDry = status == 'DRY';
    final name = plant['name'] ?? plant['id'] ?? 'النبتة';
    final vwc = (plant['vwc'] ?? 0.0) as num;
    final temp = (plant['temp'] ?? 0.0) as num;
    final humidity = (plant['humidity'] ?? 0.0) as num;

    return Column(
      children: [
        // Alert card if dry
        if (isDry)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(
              color: AppColors.danger.withOpacity(0.12),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                  color: AppColors.danger.withOpacity(0.4), width: 1.5),
            ),
            child: Row(
              children: [
                const Icon(Icons.water_drop_rounded,
                    color: AppColors.danger, size: 28),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '⚠️ $name تحتاج ماء!',
                        style: GoogleFonts.cairo(
                            color: AppColors.danger,
                            fontWeight: FontWeight.w800,
                            fontSize: 15),
                      ),
                      Text(
                        'السبالة تحلت وحدها تلقائيا — المدة: 20 دقيقة',
                        style: GoogleFonts.cairo(
                            color: AppColors.textSecondary, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                TtsButton(
                  text: '$name تحتاج ماء! السبالة تحلت وحدها.',
                  color: AppColors.danger,
                ),
              ],
            ),
          ),

        // Sensor details
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                AppColors.cardGreenLight.withOpacity(0.08),
                AppColors.cardGreenMedium.withOpacity(0.04),
              ],
            ),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: isDry
                  ? AppColors.danger.withOpacity(0.3)
                  : AppColors.cardGreenMedium.withOpacity(0.3),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    name.toString(),
                    style: GoogleFonts.cairo(
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                        color: AppColors.textHeading),
                  ),
                  const Spacer(),
                  TtsButton(
                    text:
                        '$name. الرطوبة ${vwc.toStringAsFixed(1)} بالمية. الحرارة ${temp.toStringAsFixed(1)} درجة.',
                    color: AppColors.primary,
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: _SensorCard(
                      icon: Icons.water_drop_rounded,
                      label: 'رطوبة التربة',
                      value: '${vwc.toStringAsFixed(1)}%',
                      color: AppColors.cardGreenLight,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _SensorCard(
                      icon: Icons.thermostat_rounded,
                      label: 'الحرارة',
                      value: '${temp.toStringAsFixed(1)}°C',
                      color: AppColors.cardGreenMedium,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _SensorCard(
                      icon: Icons.air_rounded,
                      label: 'الرطوبة',
                      value: '${humidity.toStringAsFixed(0)}%',
                      color: AppColors.cardGreenDark,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              // VWC progress bar
              Text('مستوى الماء في التربة',
                  style: GoogleFonts.cairo(
                      color: AppColors.textSecondary, fontSize: 12)),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: (vwc / 50).clamp(0.0, 1.0).toDouble(),
                  backgroundColor: AppColors.textMuted.withOpacity(0.15),
                  valueColor: AlwaysStoppedAnimation<Color>(
                      isDry ? AppColors.danger : AppColors.cardGreenMedium),
                  minHeight: 10,
                ),
              ),
              const SizedBox(height: 6),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('جاف جدا',
                      style: GoogleFonts.cairo(
                          color: AppColors.textMuted, fontSize: 10)),
                  Text('مثالي',
                      style: GoogleFonts.cairo(
                          color: AppColors.textMuted, fontSize: 10)),
                  Text('مشبع',
                      style: GoogleFonts.cairo(
                          color: AppColors.textMuted, fontSize: 10)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Mini live chart (simulated)
        _LiveChart(isDry: isDry),
      ],
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, end: 0);
  }
}

// ─── Live chart ───────────────────────────────────────────────────────────────
class _LiveChart extends StatelessWidget {
  const _LiveChart({required this.isDry});
  final bool isDry;

  @override
  Widget build(BuildContext context) {
    // Simulated data points
    final spots = List.generate(
      12,
      (i) => FlSpot(
        i.toDouble(),
        isDry ? 15.0 - i * 0.8 + (i % 3) * 1.2 : 30.0 + (i % 4) * 2.5,
      ),
    );

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.glassWhite,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.glassBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('رسم بياني حي',
                  style: GoogleFonts.cairo(
                      color: AppColors.textHeading,
                      fontWeight: FontWeight.w700,
                      fontSize: 14)),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text('مباشر',
                    style: GoogleFonts.cairo(
                        color: AppColors.primary,
                        fontSize: 10,
                        fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 140,
            child: LineChart(
              LineChartData(
                gridData: const FlGridData(show: false),
                titlesData: const FlTitlesData(show: false),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: spots,
                    isCurved: true,
                    color: isDry ? AppColors.danger : AppColors.primary,
                    barWidth: 3,
                    belowBarData: BarAreaData(
                      show: true,
                      color: (isDry ? AppColors.danger : AppColors.primary)
                          .withOpacity(0.1),
                    ),
                    dotData: const FlDotData(show: false),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Small components ─────────────────────────────────────────────────────────
class _StatChip extends StatelessWidget {
  const _StatChip(
      {required this.icon, required this.label, required this.color});
  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 4),
          Text(label,
              textAlign: TextAlign.center,
              style: GoogleFonts.cairo(
                  color: color, fontSize: 10, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

class _SensorCard extends StatelessWidget {
  const _SensorCard(
      {required this.icon,
      required this.label,
      required this.value,
      required this.color});
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 4),
          Text(value,
              style: GoogleFonts.cairo(
                  color: color, fontWeight: FontWeight.w900, fontSize: 15)),
          Text(label,
              textAlign: TextAlign.center,
              style: GoogleFonts.cairo(
                  color: AppColors.textMuted,
                  fontSize: 9,
                  fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _MiniSensorRow extends StatelessWidget {
  const _MiniSensorRow(
      {required this.label,
      required this.value,
      required this.icon,
      required this.color});
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: color, size: 12),
        const SizedBox(width: 4),
        Text(label,
            style: GoogleFonts.cairo(color: AppColors.textMuted, fontSize: 10)),
        const Spacer(),
        Text(value,
            style: GoogleFonts.cairo(
                color: color, fontWeight: FontWeight.w700, fontSize: 11)),
      ],
    );
  }
}
