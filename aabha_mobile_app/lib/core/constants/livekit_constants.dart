/// Topics and RPC method names the agent already speaks. These are a contract
/// with the Python side — changing one here changes nothing there.
abstract final class LivekitTopics {
  /// What the agent streams its speech back on, segment by segment.
  static const String transcription = 'lk.transcription';

  /// What the agent listens on for typed input. Its session enables text input
  /// by default, so a message sent here lands as a user turn and is answered
  /// the same way a spoken one would be — out loud.
  static const String chat = 'lk.chat';

  /// Where positions are published while the agent is guiding someone.
  static const String location = 'aabha.location';

  /// Set on each transcription stream; the same id arrives repeatedly with
  /// more text as an utterance forms.
  static const String segmentIdAttribute = 'lk.segment_id';
}

abstract final class LocationRpc {
  static const String getCurrent = 'get_current_location';
  static const String startStream = 'start_location_stream';
  static const String stopStream = 'stop_location_stream';
}

abstract final class LocationTuning {
  /// The agent waits 30s. Leaving headroom means a slow fix times out here,
  /// with a reason to explain, rather than there with none.
  static const Duration timeout = Duration(seconds: 25);

  /// A fix from the last two minutes is close enough for "where am I", and
  /// reusing it skips both the wait and a second permission prompt.
  static const Duration maxAge = Duration(minutes: 2);

  /// Metres of movement before another position is worth sending.
  static const double defaultStepMetres = 10;

  /// A car covers ten metres in under half a second, so distance alone is no
  /// limit at all on a fast road. This is the floor under how often the agent
  /// hears from us — and it cannot be raised much: at thirty metres a second a
  /// longer wait puts consecutive fixes far enough apart to step straight over
  /// the last few dozen metres before a turn, which is where "turn right now"
  /// has to be said or not said at all.
  static const Duration minSendInterval = Duration(milliseconds: 700);
}
