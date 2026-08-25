import 'dart:async';
import 'dart:convert';

import 'package:geolocator/geolocator.dart';
import 'package:livekit_client/livekit_client.dart';

import '../../core/constants/livekit_constants.dart';
import '../../core/utils/geo_math.dart';
import '../data_sources/local/location_data_source.dart';
import '../data_sources/remote/livekit_room_data_source.dart';

/// Answers the agent's three location methods.
///
/// While the agent is taking someone somewhere it needs to know where they are
/// as they move, not once. The device reports every fix its GPS produces —
/// several a second on foot — and all but one in ten metres is the same news
/// told twice, so the filtering happens here rather than over the wire and at
/// the far end.
class LocationRpcService {
  LocationRpcService({required this._location, required this._room});

  final LocationDataSource _location;
  final LivekitRoomDataSource _room;

  StreamSubscription<Position>? _watch;
  double _stepMetres = LocationTuning.defaultStepMetres;
  Position? _lastSent;
  DateTime? _lastSentAt;

  /// Said in the status line; the session carries on regardless.
  void Function(String message)? onNotice;
  void Function(String message)? onProblem;

  /// Registered before dispatch, so the methods already exist if the agent
  /// asks for a location in its very first turn.
  void register() {
    _room
      ..registerRpcMethod(LocationRpc.getCurrent, _handleCurrent)
      ..registerRpcMethod(LocationRpc.startStream, _handleStreamStart)
      ..registerRpcMethod(LocationRpc.stopStream, _handleStreamStop);
  }

  Future<String> _handleCurrent(RpcInvocationData data) async {
    final position = await _fix(maxAge: LocationTuning.maxAge);

    onNotice?.call('Shared your location with aabha');
    return jsonEncode(_asJson(position));
  }

  /// The agent asks for this when a trip starts.
  Future<String> _handleStreamStart(RpcInvocationData data) async {
    _stepMetres = _stepFrom(data.payload);

    await stop();

    // A position stream reports a refused permission to its error callback,
    // which fires long after this reply has been sent — by which time the
    // agent has already promised to call the turns. Asking once first is what
    // turns that into a refusal it can say out loud.
    final first = await _fix();
    _publish(first);

    _watch = _location.watch().listen(_onPosition, onError: _onWatchFailed);

    onNotice?.call('Sharing your location while aabha guides you');
    return jsonEncode({'streaming': true, 'step_m': _stepMetres});
  }

  Future<String> _handleStreamStop(RpcInvocationData data) async {
    await stop();
    return jsonEncode({'streaming': false});
  }

  /// Nobody is reading the positions any more, and a watch left running keeps
  /// the GPS — and the battery — busy for the rest of the day.
  Future<void> stop() async {
    await _watch?.cancel();
    _watch = null;
    _lastSent = null;
    _lastSentAt = null;
  }

  void _onPosition(Position position) {
    if (!_room.isConnected) return;

    final last = _lastSent;
    final sentAt = _lastSentAt;
    final now = DateTime.now();

    if (last != null && sentAt != null) {
      final moved = metresBetween(
        fromLat: last.latitude,
        fromLon: last.longitude,
        toLat: position.latitude,
        toLon: position.longitude,
      );

      if (moved < _stepMetres ||
          now.difference(sentAt) < LocationTuning.minSendInterval) {
        return;
      }
    }

    _publish(position);
  }

  void _publish(Position position) {
    _lastSent = position;
    _lastSentAt = DateTime.now();

    _room
        .publishJson(_asJson(position), topic: LivekitTopics.location)
        .catchError((_) {});
  }

  /// A watch can fail long after it started — a permission revoked mid-trip, a
  /// phone that loses its fix indoors. Nothing can be thrown from here, so the
  /// only honest thing is to stop and say so on screen.
  void _onWatchFailed(Object error) {
    unawaited(stop());

    final message = error is LocationException
        ? error.reason
        : 'Your location stopped coming through.';

    onProblem?.call(message);
  }

  Future<Position> _fix({Duration? maxAge}) async {
    try {
      return await _location.currentPosition(maxAge: maxAge);
    } on LocationException catch (error) {
      throw _refuse(error.reason);
    } catch (_) {
      throw _refuse(LocationRefusal.unavailable.reason);
    }
  }

  /// The reason travels back to the agent and gets read out, so it has to be
  /// an [RpcError]: a plain error is replaced with a generic "application
  /// error", losing the only part the agent could say.
  RpcError _refuse(String reason) {
    return RpcError(code: RpcError.applicationError, message: reason);
  }

  double _stepFrom(String payload) {
    try {
      final decoded = jsonDecode(payload);
      if (decoded is Map && decoded['step_m'] is num) {
        return (decoded['step_m'] as num).toDouble();
      }
    } catch (_) {
      // An unreadable payload just means the default step.
    }
    return LocationTuning.defaultStepMetres;
  }

  Map<String, dynamic> _asJson(Position position) => {
    'latitude': position.latitude,
    'longitude': position.longitude,
    'accuracy': position.accuracy,
  };
}
