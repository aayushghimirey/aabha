import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/transcript_turn.dart';
import '../../providers/voice_providers.dart';

/// The conversation, in the order it started being said.
///
/// The agent streams each utterance as it forms: the same segment id arrives
/// repeatedly with more text, so a turn already in the list is replaced rather
/// than appended to.
class TranscriptController extends Notifier<List<TranscriptTurn>> {
  // Typed turns are never transcribed back, so they need ids of their own to
  // sit in the same list as the spoken ones.
  int _typedCount = 0;

  @override
  List<TranscriptTurn> build() {
    final subscription = ref
        .watch(voiceRepositoryProvider)
        .turns
        .listen(_upsert);

    ref.onDispose(subscription.cancel);
    return const [];
  }

  void _upsert(TranscriptTurn turn) {
    final index = state.indexWhere((existing) => existing.id == turn.id);

    state = index == -1
        ? [...state, turn]
        : [...state.sublist(0, index), turn, ...state.sublist(index + 1)];
  }

  void addTyped(String text) {
    _upsert(
      TranscriptTurn(
        id: 'typed-${++_typedCount}',
        text: text,
        isMine: true,
        isFinal: true,
      ),
    );
  }

  void clear() => state = const [];
}
