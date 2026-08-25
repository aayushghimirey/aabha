/// One line of the conversation.
///
/// Spoken turns arrive repeatedly under the same [id] as the utterance forms,
/// so they are replaced rather than appended. Typed turns are never
/// transcribed back, so they get ids of their own to sit in the same list.
class TranscriptTurn {
  const TranscriptTurn({
    required this.id,
    required this.text,
    required this.isMine,
    required this.isFinal,
  });

  final String id;
  final String text;
  final bool isMine;
  final bool isFinal;

  TranscriptTurn copyWith({String? text, bool? isFinal}) => TranscriptTurn(
    id: id,
    text: text ?? this.text,
    isMine: isMine,
    isFinal: isFinal ?? this.isFinal,
  );
}
