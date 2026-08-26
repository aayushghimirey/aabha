/// What the room tells the app about itself, flattened so the presentation
/// layer never has to import the LiveKit SDK.
sealed class VoiceEvent {
  const VoiceEvent();
}

class VoiceConnected extends VoiceEvent {
  const VoiceConnected();
}

class VoiceDisconnected extends VoiceEvent {
  const VoiceDisconnected(this.reason);

  final String? reason;
}

/// Whether the agent itself is in the room. Connecting only gets you the room.
class AgentPresenceChanged extends VoiceEvent {
  const AgentPresenceChanged({required this.present});

  final bool present;
}

/// Something worth saying in the status line without losing the connection
/// state it was showing — sharing a location, starting to guide.
class VoiceNotice extends VoiceEvent {
  const VoiceNotice(this.message);

  final String message;
}

/// A failure that has to be reported but must not take the session down.
class VoiceProblem extends VoiceEvent {
  const VoiceProblem(this.message);

  final String message;
}
