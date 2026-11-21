import math

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371e3
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360

def smooth_angle(current_angle, target_angle, alpha=0.2):
    diff = (target_angle - current_angle) % 360
    if diff < -180:
        diff += 360
    if diff > 180:
        diff -= 360
    return (current_angle + diff * alpha + 360) % 360

def project_point_to_segment(lat, lon, a_lat, a_lon, b_lat, b_lon):
    dx = b_lon - a_lon
    dy = b_lat - a_lat
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return {"lat": a_lat, "lon": a_lon, "distance": calculate_distance(lat, lon, a_lat, a_lon)}
    t = max(0.0, min(1.0, ((lon - a_lon) * dx + (lat - a_lat) * dy) / len_sq))
    proj_lat = a_lat + t * dy
    proj_lon = a_lon + t * dx
    return {"lat": proj_lat, "lon": proj_lon, "distance": calculate_distance(lat, lon, proj_lat, proj_lon)}

def snap_to_route(lat, lon, route_coords):
    if not route_coords or len(route_coords) < 2:
        return {"snapped_lat": lat, "snapped_lon": lon, "distance": 0, "is_off_route": False}
    min_dist = float("inf")
    best_point = (lat, lon)
    for i in range(len(route_coords) - 1):
        p1 = route_coords[i]
        p2 = route_coords[i+1]
        proj = project_point_to_segment(lat, lon, p1[0], p1[1], p2[0], p2[1])
        if proj["distance"] < min_dist:
            min_dist = proj["distance"]
            best_point = (proj["lat"], proj["lon"])
    return {
        "snapped_lat": best_point[0],
        "snapped_lon": best_point[1],
        "distance": min_dist,
        "is_off_route": min_dist > 40.0
    }
