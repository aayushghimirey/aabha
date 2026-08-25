import 'dart:convert';

import 'package:livekit_client/livekit_client.dart';

import '../../../core/constants/livekit_constants.dart';

/// The only place the LiveKit SDK is touched.
///
/// Everything above this speaks in plain strings and callbacks, which keeps
/// the SDK out of the repositories and off the presentation layer entirely.
class LivekitRoomDataSource {
  Room? _room;

  Room? get room => _room;

  bool get isConnected => _room?.connectionState == ConnectionState.connected;

  bool get isMicrophoneEnabled =>
      _room?.localParticipant?.isMicrophoneEnabled() ?? false;

  /// True once anyone else is in the room — for this app that is the agent.
  bool get hasRemoteParticipant =>
      (_room?.remoteParticipants.isNotEmpty ?? false);

  /// Builds the room and its listener without connecting, so handlers can be
  /// registered before the first turn arrives.
  EventsListener<RoomEvent> create() {
    _room = Room(
      roomOptions: const RoomOptions(adaptiveStream: true, dynacast: true),
    );
    return _room!.createListener();
  }

  Future<void> connect({required String url, required String token}) {
    return _room!.connect(url, token);
  }

  Future<void> setMicrophoneEnabled(bool enabled) async {
    await _room?.localParticipant?.setMicrophoneEnabled(enabled);
  }

  void registerTextStreamHandler(String topic, TextStreamHandler handler) {
    _room?.registerTextStreamHandler(topic, handler);
  }

  void registerRpcMethod(String method, RpcRequestHandler handler) {
    _room?.registerRpcMethod(method, handler);
  }

  Future<void> sendText(String text, {required String topic}) async {
    await _room?.localParticipant?.sendText(
      text,
      options: SendTextOptions(topic: topic),
    );
  }

  /// A fix that does not make it is replaced by the next one a few steps
  /// later, so a failed publish is not worth interrupting a walk over.
  Future<void> publishJson(Map<String, dynamic> payload, {
    required String topic,
  }) async {
    await _room?.localParticipant?.publishData(
      utf8.encode(jsonEncode(payload)),
      reliable: true,
      topic: topic,
    );
  }

  bool isLocalIdentity(String identity) =>
      _room?.localParticipant?.identity == identity;

  Future<void> disconnect() async {
    final room = _room;
    _room = null;

    if (room == null) return;

    await room.disconnect();
    await room.dispose();
  }
}

/// Only the transcription reader's shape is needed above this layer, so it is
/// unwrapped here rather than passed up as an SDK type.
Future<void> readTranscription(
  TextStreamReader reader, {
  required void Function(String text, bool isFinal) onText,
}) async {
  var text = '';

  try {
    await for (final chunk in reader) {
      text += utf8.decode(chunk.content);
      if (text.isNotEmpty) onText(text, false);
    }
    if (text.isNotEmpty) onText(text, true);
  } catch (_) {
    // A dropped stream should never take the session with it.
  }
}

String transcriptionSegmentId(TextStreamReader reader) {
  final info = reader.info;
  return info?.attributes[LivekitTopics.segmentIdAttribute] ??
      info?.id ??
      DateTime.now().microsecondsSinceEpoch.toString();
}
