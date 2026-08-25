import 'dart:async';

import 'package:geolocator/geolocator.dart';

import '../../../core/constants/livekit_constants.dart';

/// Why a location could not be produced, in words the agent can read out.
///
/// These end up spoken, so they are phrased about the user in the third
/// person — the agent is telling them what went wrong.
enum LocationRefusal {
  denied('location permission was denied'),
  disabled('their location services are switched off'),
  unavailable('their device could not get a position fix'),
  timedOut('the location request timed out');

  const LocationRefusal(this.reason);

  final String reason;
}

class LocationException implements Exception {
  const LocationException(this.refusal);

  final LocationRefusal refusal;

  String get reason => refusal.reason;
}

class LocationDataSource {
  const LocationDataSource();

  static const LocationSettings _settings = LocationSettings(
    accuracy: LocationAccuracy.high,
    timeLimit: LocationTuning.timeout,
  );

  /// Asks once, and turns every refusal into something sayable.
  Future<void> ensurePermission() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw const LocationException(LocationRefusal.disabled);
    }

    var permission = await Geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      throw const LocationException(LocationRefusal.denied);
    }
  }

  /// A recent fix is reused when [maxAge] allows it, which skips both the wait
  /// and a second trip to the GPS.
  Future<Position> currentPosition({Duration? maxAge}) async {
    await ensurePermission();

    if (maxAge != null) {
      final last = await Geolocator.getLastKnownPosition();
      if (last != null &&
          DateTime.now().difference(last.timestamp) <= maxAge) {
        return last;
      }
    }

    try {
      return await Geolocator.getCurrentPosition(locationSettings: _settings);
    } on TimeoutException {
      throw const LocationException(LocationRefusal.timedOut);
    } on LocationServiceDisabledException {
      throw const LocationException(LocationRefusal.disabled);
    } catch (_) {
      throw const LocationException(LocationRefusal.unavailable);
    }
  }

  /// Every fix the device produces — several a second on foot. The filtering
  /// is done by the caller, not here.
  Stream<Position> watch() {
    return Geolocator.getPositionStream(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 0,
      ),
    );
  }
}
