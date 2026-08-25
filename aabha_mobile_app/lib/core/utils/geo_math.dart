import 'dart:math' as math;

/// Metres between two coordinates.
///
/// Flat-earth arithmetic: over the ten metres this has to resolve, the
/// curvature of the planet is several orders below the error on the fixes
/// themselves.
double metresBetween({
  required double fromLat,
  required double fromLon,
  required double toLat,
  required double toLon,
}) {
  const metresPerDegree = 111320.0;

  final dx =
      (toLon - fromLon) * metresPerDegree * math.cos(fromLat * math.pi / 180);
  final dy = (toLat - fromLat) * metresPerDegree;

  return math.sqrt(dx * dx + dy * dy);
}
