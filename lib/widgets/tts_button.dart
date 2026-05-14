import 'package:flutter/material.dart';
import '../core/services/tts_service.dart';
import '../core/theme/app_theme.dart';

/// A circular button that reads [text] aloud in Tunisian Arabic.
class TtsButton extends StatefulWidget {
  const TtsButton({
    super.key,
    required this.text,
    this.size = 44.0,
    this.color,
  });

  final String text;
  final double size;
  final Color? color;

  @override
  State<TtsButton> createState() => _TtsButtonState();
}

class _TtsButtonState extends State<TtsButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  bool _playing = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _toggle() async {
    if (_playing) {
      await TtsService().stop();
      setState(() => _playing = false);
      _controller.reverse();
    } else {
      setState(() => _playing = true);
      _controller.forward();
      await TtsService().speak(widget.text);
      if (mounted) {
        setState(() => _playing = false);
        _controller.reverse();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final Color btnColor = widget.color ?? AppColors.cardGreenMedium;
    return GestureDetector(
      onTap: _toggle,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeInOut,
        width: widget.size,
        height: widget.size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: _playing
              ? LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    btnColor.withOpacity(0.3),
                    btnColor.withOpacity(0.15),
                  ],
                )
              : LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    AppColors.cardGreenLight.withOpacity(0.8),
                    AppColors.cardGreenMedium,
                  ],
                ),
          boxShadow: [
            BoxShadow(
              color: _playing
                  ? btnColor.withOpacity(0.4)
                  : AppColors.cardGreenMedium.withOpacity(0.3),
              blurRadius: _playing ? 16 : 12,
              offset: const Offset(0, 4),
              spreadRadius: _playing ? 2 : 0,
            ),
          ],
          border: Border.all(
            color: _playing ? btnColor : Colors.white.withOpacity(0.4),
            width: 1.8,
          ),
        ),
        child: AnimatedScale(
          scale: _playing ? 1.1 : 1.0,
          duration: const Duration(milliseconds: 200),
          curve: Curves.elasticOut,
          child: Icon(
            _playing ? Icons.stop_rounded : Icons.volume_up_rounded,
            color: Colors.white,
            size: widget.size * 0.48,
            shadows: [
              Shadow(
                color: Colors.black.withOpacity(0.2),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
