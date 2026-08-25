import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
// The SDK exports a `Session` of its own, which is not this app's session.
import 'package:livekit_client/livekit_client.dart' hide Session;

import '../../core/constants/livekit_constants.dart';
import '../../core/network/api_exception.dart';
import '../data_sources/local/microphone_data_source.dart';
import '../data_sources/remote/livekit_room_data_source.dart';
import '../models/session.dart';
import '../models/transcript_turn.dart';
import '../models/voice_event.dart';
import '../services/location_rpc_service.dart';
import 'auth_repository.dart';

/// Owns the live session: the room, the microphone, what is said either way,
/// and the location methods the agent can call while it is open.
class VoiceRepository {
  VoiceRepository({
    required this._room,
    required this._auth,
    required this._location,
    required this._microphone,
  });

  final LivekitRoomDataSource _room;
  final AuthRepository _auth;
  final LocationRpcService _location;
  final MicrophoneDataSource _microphone;

  final _events = StreamController<VoiceEvent>.broadcast();
  final _turns = StreamController<TranscriptTurn>.broadcast();

  EventsListener<RoomEvent>? _listener;

  Stream<VoiceEvent> get events => _events.stream;
  Stream<TranscriptTurn> get turns => _turns.stream;

  bool get isMicrophoneEnabled => _room.isMicrophoneEnabled;

  Future<void> connect(Session session) async {
    try {
      // Before the room exists, so a refusal costs nothing to unwind.
      await _microphone.ensurePermission();

      final listener = _room.create();
      _listener = listener;
      _wire(listener);

      await _room.connect(
        url: session.token.serverUrl,
        token: session.token.token,
      );

      _room.registerTextStreamHandler(
        LivekitTopics.transcription,
        _onTranscription,
      );

      _location.onNotice = (message) {
        _emit(VoiceNotice(message));
      };
      _location.onProblem = (message) {
        _emit(VoiceProblem(message));
      };
      _location.register();

      await _room.setMicrophoneEnabled(true);

      // The room name is stable per user, so rejoining can land in a room
      // LiveKit already created — which fires no automatic dispatch. Asking
      // per connect is what makes leaving and coming back work.
      await _auth.dispatchAgent(session);

      _emit(const VoiceConnected());
      _emit(AgentPresenceChanged(present: _room.hasRemoteParticipant));
    } catch (error, stack) {
      // A half-open room is worse than none: tear it down before reporting,
      // or the next attempt inherits it.
      await _teardown();
      throw _describe(error, stack);
    }
  }

  /// Leaving is announced here rather than left to `RoomDisconnectedEvent`:
  /// the teardown disposes the listener, so that event would be delivered to
  /// nobody and the screen would sit there still claiming to be connected.
  /// A drop from the far end still arrives through the listener, which is
  /// alive right up until this runs.
  Future<void> disconnect() async {
    await _teardown();
    _emit(const VoiceDisconnected(null));
  }

  Future<bool> toggleMicrophone() async {
    final next = !_room.isMicrophoneEnabled;
    await _room.setMicrophoneEnabled(next);
    return next;
  }

  /// Only what is spoken comes back as transcription, so a typed turn is
  /// surfaced here or it is never seen at all.
  Future<void> sendChat(String text) async {
    await _room.sendText(text, topic: LivekitTopics.chat);
  }

  void _wire(EventsListener<RoomEvent> listener) {
    listener
      ..on<ParticipantConnectedEvent>(
        (_) => _emit(const AgentPresenceChanged(present: true)),
      )
      ..on<ParticipantDisconnectedEvent>((_) {
        // Nobody is reading the positions any more. Left alone the watch runs
        // until the app closes, holding the GPS on for the rest of the day.
        unawaited(_location.stop());
        _emit(const AgentPresenceChanged(present: false));
      })
      ..on<RoomDisconnectedEvent>((event) {
        unawaited(_location.stop());
        _emit(VoiceDisconnected(event.reason?.name));
      });
  }

  void _onTranscription(TextStreamReader reader, String participantIdentity) {
    final id = transcriptionSegmentId(reader);
    final isMine = _room.isLocalIdentity(participantIdentity);

    unawaited(
      readTranscription(
        reader,
        onText: (text, isFinal) {
          // A stream still draining when the room closes must not write into
          // a controller that is already shut.
          if (_turns.isClosed) return;

          _turns.add(
            TranscriptTurn(
              id: id,
              text: text,
              isMine: isMine,
              isFinal: isFinal,
            ),
          );
        },
      ),
    );
  }

  Future<void> _teardown() async {
    await _location.stop();
    await _listener?.dispose();
    _listener = null;
    await _room.disconnect();
  }

  /// Whatever went wrong, say enough to act on it.
  ///
  /// An earlier version collapsed every failure into "Could not join the
  /// room", which hid the one thing worth knowing — that the connect had not
  /// even reached the network yet.
  ApiException _describe(Object error, StackTrace stack) {
    if (error is ApiException) return error;

    // Always on the console, whatever the screen ends up showing.
    debugPrint('aabha: could not join the room: $error');
    debugPrintStack(stackTrace: stack, maxFrames: 8);

    // Adding a plugin does not register it in an already-running app, and the
    // symptom is this: an instant failure with no request behind it.
    if (error is MissingPluginException) {
      return const ApiException(
        'Could not join the room.\n'
        'A native plugin is not registered — stop the app completely and run '
        'it again, rather than hot restarting.',
      );
    }

    final message = error.toString();
    final looksLikeToken = RegExp(
      r'token|jwt|unauthor',
      caseSensitive: false,
    ).hasMatch(message);

    if (looksLikeToken) {
      return const ApiException(
        'Could not join the room.\n'
        'Your LiveKit token may have expired — sign out and back in.',
      );
    }

    return ApiException('Could not join the room.\n$message');
  }

  void _emit(VoiceEvent event) {
    if (!_events.isClosed) _events.add(event);
  }

  Future<void> dispose() async {
    await _teardown();
    await _events.close();
    await _turns.close();
  }
}
