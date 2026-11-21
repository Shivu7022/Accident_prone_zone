/**
 * Distance in meters between two lat/lon points using Haversine formula.
 */
export function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371e3; // Earth radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Bearing in degrees (0..360) from point 1 to point 2.
 */
export function calculateBearing(lat1, lon1, lat2, lon2) {
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;

  const y = Math.sin(deltaLambda) * Math.cos(phi2);
  const x =
    Math.cos(phi1) * Math.sin(phi2) -
    Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);

  const bearing = (Math.atan2(y, x) * 180) / Math.PI;
  return (bearing + 360) % 360;
}

/**
 * Smooth angle interpolation handling 0/360 wrap-around shortest path.
 */
export function smoothAngle(currentAngle, targetAngle, alpha = 0.2) {
  let diff = (targetAngle - currentAngle) % 360;
  if (diff < -180) diff += 360;
  if (diff > 180) diff -= 360;
  return (currentAngle + diff * alpha + 360) % 360;
}

/**
 * Project point (lat, lon) onto segment (aLat, aLon) -> (bLat, bLon).
 */
export function projectPointToSegment(lat, lon, aLat, aLon, bLat, bLon) {
  const dx = bLon - aLon;
  const dy = bLat - aLat;
  const lenSq = dx * dx + dy * dy;

  if (lenSq === 0) {
    return {
      lat: aLat,
      lon: aLon,
      distance: calculateDistance(lat, lon, aLat, aLon),
      fraction: 0,
    };
  }

  const t = Math.max(
    0,
    Math.min(1, ((lon - aLon) * dx + (lat - aLat) * dy) / lenSq)
  );

  const projLat = aLat + t * dy;
  const projLon = aLon + t * dx;
  const distance = calculateDistance(lat, lon, projLat, projLon);

  return {
    lat: projLat,
    lon: projLon,
    distance,
    fraction: t,
  };
}

/**
 * Snap current GPS coordinate to nearest segment on route polyline.
 * @param {number} lat
 * @param {number} lon
 * @param {Array<[number, number]>} routeCoordinates - Array of [lat, lon] or [lon, lat]
 */
export function snapToRoute(lat, lon, routeCoordinates = []) {
  if (!routeCoordinates || routeCoordinates.length < 2) {
    return {
      snappedLat: lat,
      snappedLon: lon,
      distance: 0,
      segmentIndex: 0,
      segmentBearing: 0,
      isOffRoute: false,
    };
  }

  let minDistance = Infinity;
  let bestPoint = { snappedLat: lat, snappedLon: lon };
  let bestIndex = 0;
  let bestBearing = 0;

  for (let i = 0; i < routeCoordinates.length - 1; i++) {
    const p1 = routeCoordinates[i];
    const p2 = routeCoordinates[i + 1];

    // Ensure lat/lon format: if coordinates are [lon, lat], normalize
    const [aLat, aLon] = p1;
    const [bLat, bLon] = p2;

    const proj = projectPointToSegment(lat, lon, aLat, aLon, bLat, bLon);
    if (proj.distance < minDistance) {
      minDistance = proj.distance;
      bestPoint = { snappedLat: proj.lat, snappedLon: proj.lon };
      bestIndex = i;
      bestBearing = calculateBearing(aLat, aLon, bLat, bLon);
    }
  }

  return {
    snappedLat: bestPoint.snappedLat,
    snappedLon: bestPoint.snappedLon,
    distance: minDistance,
    segmentIndex: bestIndex,
    segmentBearing: bestBearing,
    isOffRoute: minDistance > 40, // 40 meters off route threshold
  };
}
