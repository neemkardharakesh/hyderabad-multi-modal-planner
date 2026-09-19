"""
import_gtfs.py
--------------
Parses official GTFS datasets (HMRL Metro & TGSRTC Bus feeds) and converts
stops.txt, routes.txt, stop_times.txt, and trips.txt into the
Hyderabad One stops.json schema (stop_id, stop_name, lat, lng, mode, line_id, sequence, is_accessible).

Filters TGSRTC bus routes to key corridors matching demo areas (Gachibowli, Secunderabad, Ameerpet,
LB Nagar, HITEC City, Miyapur, Begumpet, Lingampally, Kukatpally, etc.).
Preserves MMTS suburban line entries as-is.
"""

import json
import os
import sys
import zipfile
import csv
import io
import subprocess

def parse_hmrl_gtfs(zip_path="hmrl_gtfs.zip") -> list[dict]:
    """Parses official HMRL Metro GTFS zip file."""
    if not os.path.exists(zip_path):
        print(f"[WARNING] HMRL GTFS zip '{zip_path}' not found.")
        return []

    print(f"Parsing official HMRL GTFS feed from '{zip_path}'...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        # 1. Parse routes.txt to map route_id to line_id
        route_map = {}
        if 'routes.txt' in z.namelist():
            reader = csv.DictReader(io.TextIOWrapper(z.open('routes.txt'), encoding='utf-8-sig'))
            for row in reader:
                rid = row['route_id'].upper()
                if 'RED' in rid:
                    route_map[row['route_id']] = ('red_line', 'Red Line')
                elif 'BLUE' in rid:
                    route_map[row['route_id']] = ('blue_line', 'Blue Line')
                elif 'GREEN' in rid:
                    route_map[row['route_id']] = ('green_line', 'Green Line')

        # 2. Parse stops.txt (map stop_id -> stop info)
        stops_info = {}
        if 'stops.txt' in z.namelist():
            reader = csv.DictReader(io.TextIOWrapper(z.open('stops.txt'), encoding='utf-8-sig'))
            for row in reader:
                stops_info[row['stop_id']] = row

        # 3. Map trip_id to route_id and parse stop_times.txt
        trip_route_map = {}
        if 'trips.txt' in z.namelist():
            reader = csv.DictReader(io.TextIOWrapper(z.open('trips.txt'), encoding='utf-8-sig'))
            for row in reader:
                if row['route_id'] in route_map:
                    trip_route_map[row['trip_id']] = row['route_id']

        trip_stop_times = {}
        if 'stop_times.txt' in z.namelist():
            reader = csv.DictReader(io.TextIOWrapper(z.open('stop_times.txt'), encoding='utf-8-sig'))
            for row in reader:
                tid = row['trip_id']
                if tid in trip_route_map:
                    if tid not in trip_stop_times:
                        trip_stop_times[tid] = []
                    trip_stop_times[tid].append(row)

        # 4. For each route, pick the trip with the maximum number of stations (full route)
        route_sequences = {}
        for rid in route_map:
            rid_trips = [tid for tid, r in trip_route_map.items() if r == rid and tid in trip_stop_times]
            if rid_trips:
                best_trip = max(rid_trips, key=lambda tid: len(trip_stop_times[tid]))
                route_sequences[rid] = trip_stop_times[best_trip]

        # 5. Build Metro stops list
        metro_stops = []
        for rid, line_tuple in route_map.items():
            line_id, line_label = line_tuple
            st_list = route_sequences.get(rid, [])
            st_list = sorted(st_list, key=lambda x: int(x['stop_sequence']))
            
            seen_parent_ids = set()
            seq_counter = 0

            for st in st_list:
                sid = st['stop_id']
                s_data = stops_info.get(sid, {})
                parent_id = s_data.get('parent_station') or sid
                
                if parent_id in seen_parent_ids:
                    continue
                seen_parent_ids.add(parent_id)

                p_data = stops_info.get(parent_id, s_data)
                name = p_data.get('stop_name', sid).strip()
                if "Mahatma Gandhi Bus Station" in name or "MGBS" in name:
                    clean_name = "MGBS Metro Station"
                elif "JBS" in name or "Parade Ground" in name:
                    clean_name = "JBS Parade Ground Metro Station"
                elif not name.endswith("Metro Station"):
                    clean_name = f"{name} Metro Station"
                else:
                    clean_name = name

                lat = float(p_data.get('stop_lat', 0.0))
                lng = float(p_data.get('stop_lon', 0.0))

                metro_stops.append({
                    "stop_id": f"gtfs_metro_{line_id}_{seq_counter:02d}",
                    "stop_name": clean_name,
                    "lat": round(lat, 7),
                    "lng": round(lng, 7),
                    "mode": "metro",
                    "line_id": line_id,
                    "sequence": seq_counter,
                    "is_accessible": True
                })
                seq_counter += 1

    print(f"Extracted {len(metro_stops)} official HMRL Metro GTFS stops across Red, Blue, and Green lines.")
    return metro_stops


def parse_tgsrtc_gtfs(zip_path="tgsrtc_gtfs.zip") -> list[dict]:
    """Parses official TGSRTC Bus GTFS zip file and filters bus routes for demo corridors."""
    if not os.path.exists(zip_path):
        print(f"[WARNING] TGSRTC GTFS zip '{zip_path}' not found.")
        return []

    print(f"Parsing official TGSRTC Bus GTFS feed from '{zip_path}'...")
    DEMO_KEYWORDS = [
        "gachibowli", "secunderabad", "ameerpet", "lb nagar", "hitec", "hitech",
        "miyapur", "begumpet", "lingampally", "kukatpally", "kphb", "jbs", "mgbs",
        "patny", "paradise", "jubilee", "punjagutta", "charminar", "nampally",
        "khairatabad", "raidurg", "falaknuma"
    ]

    with zipfile.ZipFile(zip_path, 'r') as z:
        stops = {s['stop_id']: s for s in csv.DictReader(io.TextIOWrapper(z.open('stops.txt'), encoding='utf-8-sig'))}

        trip_routes = {}
        if 'trips.txt' in z.namelist():
            for row in csv.DictReader(io.TextIOWrapper(z.open('trips.txt'), encoding='utf-8-sig')):
                trip_routes[row['trip_id']] = row['route_id']

        route_stop_times = {}
        if 'stop_times.txt' in z.namelist():
            for row in csv.DictReader(io.TextIOWrapper(z.open('stop_times.txt'), encoding='utf-8-sig')):
                tid = row['trip_id']
                rid = trip_routes.get(tid)
                if rid:
                    if rid not in route_stop_times:
                        route_stop_times[rid] = {}
                    if tid not in route_stop_times[rid]:
                        route_stop_times[rid][tid] = []
                    route_stop_times[rid][tid].append(row)

        # Filter bus routes matching demo keywords
        matching_routes = []
        for rid, trips_dict in route_stop_times.items():
            sample_trip = max(trips_dict.values(), key=lambda x: len(x))
            stop_names = [stops[st['stop_id']]['stop_name'].lower() for st in sample_trip if st['stop_id'] in stops]
            matched_kws = [kw for kw in DEMO_KEYWORDS if any(kw in name for name in stop_names)]
            if len(matched_kws) >= 4 or rid == '216':
                matching_routes.append((rid, len(matched_kws), sample_trip))

        # Sort matching routes by relevance score and select top key routes
        matching_routes.sort(key=lambda x: x[1], reverse=True)
        selected_bus_routes = matching_routes[:12]

        bus_stops = []
        seen_bus_stop_ids = set()

        for rid, score, sample_trip in selected_bus_routes:
            sorted_st = sorted(sample_trip, key=lambda x: int(x['stop_sequence']))
            line_id = f"route_{rid.replace('/', '_')}"
            seq_counter = 0

            for st in sorted_st:
                sid = st['stop_id']
                s_data = stops.get(sid)
                if not s_data:
                    continue

                name = s_data.get('stop_name', sid).strip()
                lat = float(s_data.get('stop_lat', 0.0))
                lng = float(s_data.get('stop_lon', 0.0))

                custom_stop_id = f"gtfs_bus_{line_id}_{seq_counter:02d}"
                if custom_stop_id in seen_bus_stop_ids:
                    continue
                seen_bus_stop_ids.add(custom_stop_id)

                bus_stops.append({
                    "stop_id": custom_stop_id,
                    "stop_name": name,
                    "lat": round(lat, 7),
                    "lng": round(lng, 7),
                    "mode": "bus",
                    "line_id": line_id,
                    "sequence": seq_counter,
                    "is_accessible": False
                })
                seq_counter += 1

    print(f"Extracted {len(bus_stops)} official TGSRTC Bus GTFS stops across top {len(selected_bus_routes)} demo corridor bus routes.")
    return bus_stops


def import_and_merge_gtfs():
    """Merges GTFS Metro and TGSRTC Bus data with existing MMTS data into stops.json."""
    stops_json_path = "stops.json"
    if not os.path.exists(stops_json_path):
        print(f"[ERROR] {stops_json_path} not found.")
        return

    with open(stops_json_path, 'r', encoding='utf-8') as f:
        existing_data = json.load(f)

    # Ensure all existing stops have stop_id set
    for s in existing_stops:
        if "stop_id" not in s:
            sid = s.get("id") or f"stop_{s.get('stop_name', 'unknown')}"
            s["stop_id"] = sid
            print(f"[WARNING] Normalizing stop missing 'stop_id' in existing stops.json: {s}")

    # Keep existing MMTS stops
    mmts_stops = [s for s in existing_stops if s.get("mode") == "mmts"]
    print(f"Preserving {len(mmts_stops)} MMTS suburban line stops.")

    # Parse HMRL Metro GTFS zip
    gtfs_metro_stops = parse_hmrl_gtfs("hmrl_gtfs.zip")

    # Parse TGSRTC Bus GTFS zip
    gtfs_bus_stops = parse_tgsrtc_gtfs("tgsrtc_gtfs.zip")

    if not gtfs_bus_stops:
        print("[INFO] Fallback to existing bus corridor dataset.")
        gtfs_bus_stops = [s for s in existing_stops if s.get("mode") == "bus"]

    # Combine all stops
    combined_stops = gtfs_bus_stops + gtfs_metro_stops + mmts_stops

    # Deduplicate by stop_id
    final_stops = []
    seen_ids = set()
    for s in combined_stops:
        sid = s.get("stop_id") or s.get("id")
        if not sid:
            print(f"[WARNING] Skipping malformed stop missing stop_id and id: {s}")
            continue
        s["stop_id"] = sid
        if sid not in seen_ids:
            seen_ids.add(sid)
            final_stops.append(s)

    new_payload = {"stops": final_stops}
    with open(stops_json_path, 'w', encoding='utf-8') as f:
        json.dump(new_payload, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Updated 'stops.json' with {len(final_stops)} total stops.")

    # Re-run build_graph.py
    print("\nRebuilding transport network graph (build_graph.py)...")
    res = subprocess.run([sys.executable, "build_graph.py"], capture_output=True, text=True)
    print(res.stdout)

    # Re-run test_planner.py
    print("\nExecuting test_planner.py verification suite...")
    res_test = subprocess.run([sys.executable, "test_planner.py"], capture_output=True, text=True)
    print(res_test.stdout)


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    import_and_merge_gtfs()
