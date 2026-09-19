"""
build_graph.py
--------------
Multi-modal public transport route graph builder for Hyderabad, India.
Loads stops.json, constructs a NetworkX graph with direct transit edges
and walking transfer edges, and saves the graph for downstream routing.
"""

import json
import math
import os
import pickle
import sys
import networkx as nx

# -----------------------------------------------------------------------------
# FARE & SPEED CONFIGURATION PARAMETERS (PLACEHOLDERS)
# -----------------------------------------------------------------------------
# Travel speeds & hop times in minutes:
# - Metro: ~2.5 minutes per stop hop
# - Bus: ~4.0 minutes per stop hop
# - MMTS: ~3.0 minutes per stop hop
# - Walking speed: 5.0 km/h (~83.33 meters per minute)

MODE_HOP_TIME_MIN = {
    "metro": 2.5,
    "bus": 4.0,
    "mmts": 3.0
}

WALKING_SPEED_KMH = 5.0
WALKING_SPEED_MPM = (WALKING_SPEED_KMH * 1000.0) / 60.0  # ~83.33 m/min
TRANSFER_MAX_DISTANCE_M = 500.0  # 500 meters maximum transfer distance

# Fare model parameters (in INR / ₹):
# NOTE: These fare values are reasonable placeholder estimates for hackathon demo.
# They should be verified against official TSRTC, HMRL, and SCR MMTS fare charts.
def calculate_metro_fare(dist_km: float) -> float:
    """
    Calculates official Hyderabad Metro Rail (HMRL) distance-based fare slabs:
    - 0 to 2 km: ₹10
    - >2 to 4 km: ₹15
    - >4 to 6 km: ₹25
    - >6 to 8 km: ₹30
    - >8 to 10 km: ₹35
    - >10 to 14 km: ₹40
    - >14 to 18 km: ₹45
    - >18 to 22 km: ₹50
    - >22 to 26 km: ₹55
    - >26+ km: ₹60
    """
    if dist_km <= 2.0:
        return 10.0
    elif dist_km <= 4.0:
        return 15.0
    elif dist_km <= 6.0:
        return 25.0
    elif dist_km <= 8.0:
        return 30.0
    elif dist_km <= 10.0:
        return 35.0
    elif dist_km <= 14.0:
        return 40.0
    elif dist_km <= 18.0:
        return 45.0
    elif dist_km <= 22.0:
        return 50.0
    elif dist_km <= 26.0:
        return 55.0
    else:
        return 60.0


def calculate_direct_fare(mode: str, dist_m: float = 1000.0) -> float:
    """
    Calculates single-hop fare estimate per transit mode.
    - Metro: HMRL distance-based fare slab
    - Bus: ₹10 flat base fare
    - MMTS: ₹10 flat fare
    """
    dist_km = dist_m / 1000.0
    if mode == "metro":
        return calculate_metro_fare(dist_km)
    elif mode == "bus":
        return 10.0
    elif mode == "mmts":
        return 10.0
    return 10.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two geographic coordinates
    in meters using the Haversine formula.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def build_graph(stops_json_path: str = "stops.json") -> tuple[nx.Graph, dict]:
    """
    Loads stops.json and constructs a multi-modal transport graph.
    Returns (G, stop_lookup) where:
    - G: networkx.Graph with direct and transfer edges
    - stop_lookup: dict mapping stop_id to complete stop details
    """
    if not os.path.exists(stops_json_path):
        raise FileNotFoundError(f"Stops file not found at '{stops_json_path}'. Run fetch_transit_data.py first.")

    with open(stops_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stops = data.get("stops", [])
    stop_lookup = {}
    for stop in stops:
        sid = stop.get("stop_id") or stop.get("id")
        if not sid:
            print(f"[WARNING] Skipping stop missing stop_id and id: {stop}")
            continue
        stop_entry = dict(stop)
        stop_entry["stop_id"] = sid
        stop_lookup[sid] = stop_entry

    G = nx.Graph()

    # 1. Add all stops as graph nodes with metadata
    for stop in stops:
        sid = stop.get("stop_id") or stop.get("id")
        if not sid:
            continue
        G.add_node(
            sid,
            stop_id=sid,
            stop_name=stop.get("stop_name", sid),
            lat=stop.get("lat", 0.0),
            lng=stop.get("lng", 0.0),
            mode=stop.get("mode", "bus"),
            line_id=stop.get("line_id", ""),
            sequence=stop.get("sequence", 0),
            is_accessible=stop.get("is_accessible", stop.get("mode") == "metro")
        )

    # 2. Add Direct Edges between consecutive stops in the same corridor/line
    # Group stops by line_id and sort by sequence
    corridors = {}
    for stop in stops:
        line_id = stop["line_id"]
        if line_id not in corridors:
            corridors[line_id] = []
        corridors[line_id].append(stop)

    direct_edge_count = 0
    for line_id, line_stops in corridors.items():
        sorted_stops = sorted(line_stops, key=lambda s: s["sequence"])
        mode = sorted_stops[0]["mode"]
        hop_time = MODE_HOP_TIME_MIN.get(mode, 3.0)

        for i in range(len(sorted_stops) - 1):
            u = sorted_stops[i]
            v = sorted_stops[i + 1]

            # Calculate actual physical distance between consecutive stops using Haversine formula
            dist_m = haversine_distance(u["lat"], u["lng"], v["lat"], v["lng"])
            hop_fare = calculate_direct_fare(mode, dist_m)

            G.add_edge(
                u["stop_id"],
                v["stop_id"],
                weight=hop_time,            # Weight in minutes for Dijkstra routing
                travel_time=hop_time,       # Travel time in minutes
                fare=hop_fare,              # Fare estimate in INR (₹)
                type="direct",              # Edge type identifier
                line_id=line_id,
                mode=mode,
                distance_m=round(dist_m, 1)
            )
            direct_edge_count += 1

    # 3. Add Transfer Edges between stops from DIFFERENT corridors/modes < 500m
    transfer_edge_count = 0
    transfer_edges_list = []

    for i in range(len(stops)):
        for j in range(i + 1, len(stops)):
            u = stops[i]
            v = stops[j]

            # Transfers only occur between DIFFERENT lines/corridors
            if u["line_id"] == v["line_id"]:
                continue

            dist_m = haversine_distance(u["lat"], u["lng"], v["lat"], v["lng"])

            if dist_m <= TRANSFER_MAX_DISTANCE_M:
                # Calculate walking time at 5 km/h pace
                walk_time_min = round(dist_m / WALKING_SPEED_MPM, 2)

                # Transfer buffer rule:
                # - Same-station transfer (dist < 5m): minimum 3 minutes platform change / wait buffer
                # - Walking transfer (<500m): actual walk time + flat 2 minutes boarding wait buffer
                if dist_m < 5.0:
                    transfer_time_min = 3.0
                else:
                    transfer_time_min = round(walk_time_min + 2.0, 2)

                G.add_edge(
                    u["stop_id"],
                    v["stop_id"],
                    weight=transfer_time_min,       # Total transfer time in minutes (weight for Dijkstra)
                    travel_time=transfer_time_min,  # Travel time in minutes
                    walk_time_min=walk_time_min,    # Pure walking time in minutes
                    fare=0.0,                       # Free transfer walk (₹0)
                    type="transfer",                # Edge type identifier
                    line_id="transfer_walk",
                    mode="walk",
                    distance_m=round(dist_m, 1)
                )

                transfer_edge_count += 1
                transfer_edges_list.append({
                    "from_id": u["stop_id"],
                    "from_name": u["stop_name"],
                    "from_mode": u["mode"],
                    "from_line": u["line_id"],
                    "to_id": v["stop_id"],
                    "to_name": v["stop_name"],
                    "to_mode": v["mode"],
                    "to_line": v["line_id"],
                    "distance_m": round(dist_m, 1),
                    "walk_time_min": walk_time_min,
                    "transfer_time_min": transfer_time_min
                })

    return G, stop_lookup, transfer_edges_list


def export_graph_data(G: nx.Graph, stop_lookup: dict, transfer_edges: list):
    """Saves the graph structure as a pickle file and JSON for task usage."""
    # 1. Save as pickle file for direct Python object loading
    pickle_filename = "graph.pickle"
    with open(pickle_filename, "wb") as f:
        pickle.dump({"graph": G, "stop_lookup": stop_lookup}, f)

    # 2. Save as JSON format for clear inspection & language-agnostic export
    json_filename = "graph_data.json"
    nodes_data = []
    for node_id, data in G.nodes(data=True):
        nodes_data.append({"id": node_id, "stop_id": data.get("stop_id", node_id), **data})

    edges_data = []
    for u, v, data in G.edges(data=True):
        edges_data.append({
            "from": u,
            "to": v,
            "from_name": stop_lookup[u]["stop_name"],
            "to_name": stop_lookup[v]["stop_name"],
            **data
        })

    graph_json = {
        "summary": {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "direct_edges": sum(1 for _, _, d in G.edges(data=True) if d.get("type") == "direct"),
            "transfer_edges": sum(1 for _, _, d in G.edges(data=True) if d.get("type") == "transfer"),
        },
        "nodes": nodes_data,
        "edges": edges_data
    }

    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(graph_json, f, indent=2, ensure_ascii=False)

    return pickle_filename, json_filename


def main():
    """Main execution block to build graph, print summary, and export."""
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("==================================================================")
    print("        HYDERABAD MULTI-MODAL ROUTE GRAPH BUILDER")
    print("==================================================================")
    print("Loading 'stops.json' and building network graph...\n")

    G, stop_lookup, transfer_edges = build_graph("stops.json")

    pickle_file, json_file = export_graph_data(G, stop_lookup, transfer_edges)

    direct_count = sum(1 for _, _, d in G.edges(data=True) if d.get("type") == "direct")
    transfer_count = len(transfer_edges)

    print("==================================================================")
    print("                      GRAPH SUMMARY REPORT                        ")
    print("==================================================================")
    print(f"  • Total Nodes (Transit Stops) : {G.number_of_nodes()}")
    print(f"  • Total Edges                : {G.number_of_edges()}")
    print(f"  • Direct In-Vehicle Edges    : {direct_count}")
    print(f"  • Walking Transfer Edges (<500m): {transfer_count}")
    print("==================================================================\n")

    print("Multi-Modal Transfer Connections Found (Walking < 500m):")
    print("-" * 80)
    for idx, t in enumerate(transfer_edges, 1):
        print(f"{idx:2d}. [{t['from_mode'].upper()}] {t['from_name']} ({t['from_line']})")
        print(f"    <---> [{t['to_mode'].upper()}] {t['to_name']} ({t['to_line']})")
        print(f"    Distance: {t['distance_m']}m | Walk Time: ~{t['walk_time_min']} mins\n")
    print("-" * 80)

    if transfer_count > 0:
        print(f"\n[VERIFIED] Corridors successfully INTERSECT at {transfer_count} transfer points.")
        print("           Multi-modal routing (Bus <-> Metro <-> MMTS) is ready!\n")
    else:
        print("\n[WARNING] No transfer edges found under 500m threshold.")

    print(f"Graph exported successfully to:")
    print(f"  1. Binary Pickle : '{pickle_file}'")
    print(f"  2. JSON Data     : '{json_file}'\n")


if __name__ == "__main__":
    main()
