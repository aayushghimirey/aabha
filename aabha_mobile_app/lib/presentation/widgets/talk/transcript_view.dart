import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_dimens.dart';
import '../../../data/models/transcript_turn.dart';

class TranscriptView extends StatefulWidget {
  const TranscriptView({super.key, required this.turns});

  final List<TranscriptTurn> turns;

  @override
  State<TranscriptView> createState() => _TranscriptViewState();
}

class _TranscriptViewState extends State<TranscriptView> {
  final _scroll = ScrollController();

  @override
  void didUpdateWidget(TranscriptView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.turns.length >= oldWidget.turns.length) _stickToBottom();
  }

  /// A partial utterance grows a line at a time; the view has to follow it.
  void _stickToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 300,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.panelAlt,
        border: Border.all(color: AppColors.line),
        borderRadius: BorderRadius.circular(12),
      ),
      child: widget.turns.isEmpty
          ? Center(
              child: Text(
                'Nothing said yet.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            )
          : ListView.separated(
              controller: _scroll,
              itemCount: widget.turns.length,
              separatorBuilder: (_, _) =>
                  const SizedBox(height: AppDimens.gap),
              itemBuilder: (context, index) =>
                  _Turn(turn: widget.turns[index]),
            ),
    );
  }
}

class _Turn extends StatelessWidget {
  const _Turn({required this.turn});

  final TranscriptTurn turn;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: turn.isMine
          ? CrossAxisAlignment.end
          : CrossAxisAlignment.start,
      children: [
        Text(turn.isMine ? 'You' : 'aabha', style: theme.textTheme.labelSmall),
        const SizedBox(height: 3),
        Opacity(
          // A turn still being said is shown, but shown as unfinished.
          opacity: turn.isFinal ? 1 : 0.65,
          child: Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.sizeOf(context).width * 0.7,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
            decoration: BoxDecoration(
              color: turn.isMine ? AppColors.accent : AppColors.bubbleThem,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              turn.text,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: turn.isMine ? Colors.white : AppColors.text,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
