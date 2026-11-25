HUB_COORDS = {
    "Benguet": (16.4550, 120.6200),
    "Bukidnon": (8.3667, 124.8639),
    "Tangub City": (8.0619, 123.7486),
    "Metro Manila": (14.5995, 120.9842),
    "Cebu": (10.3157, 123.8854),
    "Davao": (7.1907, 125.4553),
}

REGION_DISTANCES_KM = {
    ("Benguet", "Metro Manila"): 250.0,
    ("Benguet", "Cebu"): 820.0,
    ("Benguet", "Davao"): 1250.0,
    ("Bukidnon", "Metro Manila"): 980.0,
    ("Bukidnon", "Cebu"): 340.0,
    ("Bukidnon", "Davao"): 210.0,
    ("Tangub City", "Cebu"): 260.0,
    ("Tangub City", "Davao"): 330.0,
    ("Tangub City", "Metro Manila"): 890.0,
}


def get_coords(place):
    if not place:
        return (12.8797, 121.7740)
    clean = place.strip()
    if clean in HUB_COORDS:
        return HUB_COORDS[clean]
    for name, coords in HUB_COORDS.items():
        if name.lower() in clean.lower() or clean.lower() in name.lower():
            return coords
    return (12.8797, 121.7740)


def estimate_distance_km(origin_region, destination_hub):
    key = (origin_region.strip(), destination_hub.strip())
    if key in REGION_DISTANCES_KM:
        return REGION_DISTANCES_KM[key]
    rev = (destination_hub.strip(), origin_region.strip())
    if rev in REGION_DISTANCES_KM:
        return REGION_DISTANCES_KM[rev]
    return 300.0 if origin_region.strip().lower() != destination_hub.strip().lower() else 65.0


def get_route_path(origin_region, destination_hub):
    origin_coords = get_coords(origin_region)
    dest_coords = get_coords(destination_hub)
    mid_lat = (origin_coords[0] + dest_coords[0]) / 2 + 0.35
    mid_lon = (origin_coords[1] + dest_coords[1]) / 2 - 0.25
    return origin_coords, dest_coords, [origin_coords, (mid_lat, mid_lon), dest_coords]


def build_ai_plan(batches, orders, cold_chain=True, truck_capacity_kg=3000.0):
    supply_by_crop = {}
    for b in batches:
        if b.get("status") == "AVAILABLE":
            crop = b["crop_name"].strip().title()
            supply_by_crop[crop] = supply_by_crop.get(crop, 0.0) + float(b["quantity_kg"])

    demand_by_crop = {}
    for o in orders:
        if o.get("status") == "PENDING":
            crop = o["crop_name"].strip().title()
            demand_by_crop[crop] = demand_by_crop.get(crop, 0.0) + float(o["demand_kg"])

    all_crops = sorted(set(supply_by_crop) | set(demand_by_crop))
    forecasts = []
    alerts = []

    for crop in all_crops:
        sup = supply_by_crop.get(crop, 0.0)
        dem = demand_by_crop.get(crop, 0.0)
        predicted_7d_demand = round(max(dem, sup * 0.85) * 1.15, 1)
        surplus_kg = round(sup - dem, 1)

        if surplus_kg > 500:
            alert_msg = f"SURPLUS ALERT: {surplus_kg} kg of {crop} -> Route excess to food processors/canning."
            alerts.append(alert_msg)
        elif surplus_kg < -200:
            alert_msg = f"SHORTAGE ALERT: Need {abs(surplus_kg)} kg more {crop} -> Cluster nearby co-ops."
            alerts.append(alert_msg)
        else:
            alert_msg = f"BALANCED: {crop} supply and buyer demand closely aligned."

        forecasts.append({
            "crop": crop,
            "supply_kg": round(sup, 1),
            "demand_kg": round(dem, 1),
            "forecast_7d_kg": predicted_7d_demand,
            "surplus_or_gap_kg": surplus_kg,
            "status_note": alert_msg,
        })

    proposed_routes = []
    idx = 1
    for b in batches:
        if b.get("status") != "AVAILABLE":
            continue
        matching_order = next(
            (
                o for o in orders
                if o.get("status") == "PENDING"
                and o["crop_name"].strip().lower() == b["crop_name"].strip().lower()
            ),
            None,
        )
        dest = matching_order["hub_location"] if matching_order else "Metro Manila"
        origin = b.get("region", "Benguet")
        dist_km = estimate_distance_km(origin, dest)
        spoilage_pct = 9.5 if cold_chain else 36.0
        qty = min(float(b["quantity_kg"]), float(truck_capacity_kg))
        crop_forecast = next((f for f in forecasts if f["crop"] == b["crop_name"].strip().title()), None)
        surplus_flag = (
            crop_forecast["status_note"]
            if crop_forecast and crop_forecast["surplus_or_gap_kg"] > 500
            else "Standard Cold-Chain Dispatch"
        )

        proposed_routes.append({
            "vehicle_code": f"COLD-{100 + idx}" if cold_chain else f"TRK-{200 + idx}",
            "cold_chain": 1 if cold_chain else 0,
            "capacity_kg": qty,
            "origin_region": origin,
            "destination_hub": dest,
            "estimated_km": dist_km,
            "est_spoilage_pct": spoilage_pct,
            "surplus_alert": surplus_flag,
        })
        idx += 1

    return {
        "forecasts": forecasts,
        "alerts": alerts,
        "proposed_routes": proposed_routes,
    }