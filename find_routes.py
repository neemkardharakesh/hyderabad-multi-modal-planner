"""
find_routes.py
--------------
Multi-modal journey planner for Hyderabad public transport.
Implements shortest-path routing (Dijkstra / multi-objective search) across
Bus, Metro, and MMTS networks with walking transfers.
"""

import json
import os
import pickle
import sys
import difflib
import itertools
import networkx as nx

def load_graph_and_lookup(pickle_path="graph.pickle", json_path="graph_data.json"):
    """Loads the route graph and stop lookup dict from pickle or JSON export."""
    if os.path.exists(pickle_path):
        with open(pickle_path, "rb") as f:
            data = pickle.load(f)
            return data["graph"], data["stop_lookup"]
    elif os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stop_lookup = {node["id"]: node for node in data["nodes"]}
        G = nx.Graph()
        for node in data["nodes"]:
            G.add_node(node["id"], **node)
        for edge in data["edges"]:
            G.add_edge(edge["from"], edge["to"], **{k: v for k, v in edge.items() if k not in ("from", "to")})
        return G, stop_lookup
    else:
        raise FileNotFoundError("Graph data files not found. Run build_graph.py first.")


def get_closest_stop_names(query: str, stop_lookup: dict, n: int = 3) -> list[str]:
    """
    Finds up to `n` closest matching stop names in `stop_lookup` for an unmatched query string.
    Uses string similarity ratio and token overlap.
    """
    unique_names = list(dict.fromkeys(info["stop_name"] for info in stop_lookup.values()))
    query_clean = query.strip().lower()

    def score_name(name: str) -> float:
        name_lower = name.lower()
        ratio = difflib.SequenceMatcher(None, query_clean, name_lower).ratio()
        q_tokens = set(query_clean.split())
        n_tokens = set(name_lower.split())
        overlap = len(q_tokens.intersection(n_tokens))
        sub = 0.3 if (query_clean in name_lower or name_lower in query_clean) else 0.0
        return ratio + 0.4 * overlap + sub

    ranked = sorted(unique_names, key=score_name, reverse=True)
    return ranked[:n]


def resolve_stop(query: str, stop_lookup: dict) -> list[str]:
    """
    Resolves a stop name / landmark query string to matching stop_ids.
    Performs case-insensitive exact substring matching, token matching, and fuzzy matching.
    """
    query_clean = query.strip().lower()
    matches = []

    # 1. Exact or substring match
    for stop_id, info in stop_lookup.items():
        name_lower = info["stop_name"].lower()
        if query_clean == name_lower or query_clean in name_lower or name_lower in query_clean:
            matches.append(stop_id)

    if matches:
        return list(dict.fromkeys(matches))

    # 2. Word token match (e.g. "Secunderabad" matching "Secunderabad Junction Railway Station")
    query_tokens = set(query_clean.split())
    for stop_id, info in stop_lookup.items():
        name_tokens = set(info["stop_name"].lower().split())
        if query_tokens.intersection(name_tokens):
            matches.append(stop_id)

    if matches:
        return matches

    # 3. Fuzzy match fallback
    names = [info["stop_name"] for info in stop_lookup.values()]
    close_matches = difflib.get_close_matches(query, names, n=3, cutoff=0.6)
    for stop_id, info in stop_lookup.items():
        if info["stop_name"] in close_matches:
            matches.append(stop_id)

    return list(dict.fromkeys(matches))


def calculate_metro_fare(dist_km: float) -> float:
    """
    Official Hyderabad Metro Rail (HMRL) distance-based fare structure:
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


def calculate_segment_fare(mode: str, stop_count: int, dist_m: float = 0.0) -> float:
    """
    Calculates single-ticket fare for a continuous segment of `stop_count` hops.
    - Metro: HMRL official distance-based fare slabs (₹10 to ₹60)
    - Bus: ₹10 base + stage distance fare
    - MMTS: ₹10 flat rate per continuous MMTS trip
    - Walk: ₹0
    """
    dist_km = dist_m / 1000.0
    if mode == "metro":
        return calculate_metro_fare(dist_km)
    elif mode == "bus":
        if dist_km > 0:
            if dist_km <= 3.0:
                return 10.0
            elif dist_km <= 7.0:
                return 15.0
            elif dist_km <= 12.0:
                return 25.0
            elif dist_km <= 18.0:
                return 35.0
            elif dist_km <= 25.0:
                return 45.0
            else:
                return 50.0
        return float(min(50.0, max(10.0, stop_count * 10.0)))
    elif mode == "mmts":
        return 10.0
    return 0.0


def format_duration_str(minutes: float) -> str:
    """Formats duration in minutes into a human-readable string (e.g. 45 min, 1 hr 15 min)."""
    m = round(minutes)
    if m < 60:
        return f"{m} min"
    hrs = m // 60
    rem_mins = m % 60
    if rem_mins == 0:
        return f"{hrs} hr" if hrs == 1 else f"{hrs} hrs"
    return f"{hrs} hr {rem_mins} min" if hrs == 1 else f"{hrs} hrs {rem_mins} min"


def parse_path_to_steps(G: nx.Graph, path: list[str], stop_lookup: dict) -> tuple[list[dict], float, float, int]:
    """
    Converts a node path list [s0, s1, s2, ...] into aggregated journey steps.
    Returns (steps, total_time_minutes, total_fare_rupees, num_transfers).
    """
    if len(path) < 2:
        return [], 0.0, 0.0, 0

    raw_hops = []
    total_time = 0.0

    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        edge = G[u][v]

        travel_time = edge.get("travel_time", edge.get("weight", 0.0))
        edge_type = edge.get("type", "direct")
        line_id = edge.get("line_id", "transit")
        mode = edge.get("mode", "transit")

        total_time += travel_time

        raw_hops.append({
            "from_id": u,
            "from_name": stop_lookup[u]["stop_name"],
            "to_id": v,
            "to_name": stop_lookup[v]["stop_name"],
            "mode": mode,
            "line_id": line_id,
            "edge_type": edge_type,
            "travel_time": travel_time,
            "distance_m": edge.get("distance_m", 0.0)
        })

    # Aggregate consecutive hops on the same line/corridor or consecutive walk transfers into clean steps
    steps = []
    if not raw_hops:
        return steps, total_time, 0.0, 0

    curr = raw_hops[0].copy()
    curr_stop_count = 1
    curr_from_id = curr["from_id"]
    curr_from_name = curr["from_name"]
    curr_time = curr["travel_time"]
    curr_distance_m = curr.get("distance_m", 0.0)
    curr_stops_sequence = [curr["from_id"], curr["to_id"]]

    for next_hop in raw_hops[1:]:
        same_segment = (
            (next_hop["line_id"] == curr["line_id"] and next_hop["edge_type"] == curr["edge_type"] and next_hop["edge_type"] != "transfer") or
            (next_hop["edge_type"] == "transfer" and curr["edge_type"] == "transfer")
        )
        if same_segment:
            curr_stop_count += 1
            curr["to_id"] = next_hop["to_id"]
            curr["to_name"] = next_hop["to_name"]
            curr_time += next_hop["travel_time"]
            curr_distance_m += next_hop.get("distance_m", 0.0)
            curr_stops_sequence.append(next_hop["to_id"])
        else:
            seg_fare = calculate_segment_fare(curr["mode"], curr_stop_count, curr_distance_m) if curr["edge_type"] != "transfer" else 0.0
            from_info = stop_lookup.get(curr_from_id, {})
            to_info = stop_lookup.get(curr["to_id"], {})

            inter_stops = [
                {
                    "stop_id": sid,
                    "stop_name": stop_lookup[sid]["stop_name"],
                    "lat": stop_lookup[sid].get("lat"),
                    "lng": stop_lookup[sid].get("lng")
                }
                for sid in curr_stops_sequence[1:-1]
                if sid in stop_lookup
            ]
            all_step_stops = [
                {
                    "stop_id": sid,
                    "stop_name": stop_lookup[sid]["stop_name"],
                    "lat": stop_lookup[sid].get("lat"),
                    "lng": stop_lookup[sid].get("lng")
                }
                for sid in curr_stops_sequence
                if sid in stop_lookup
            ]

            steps.append({
                "mode": curr["mode"],
                "line_id": curr["line_id"],
                "edge_type": curr["edge_type"],
                "from_stop": curr_from_name,
                "from_id": curr_from_id,
                "from_lat": from_info.get("lat"),
                "from_lng": from_info.get("lng"),
                "to_stop": curr["to_name"],
                "to_id": curr["to_id"],
                "to_lat": to_info.get("lat"),
                "to_lng": to_info.get("lng"),
                "stop_count": curr_stop_count if curr["edge_type"] != "transfer" else 0,
                "time_minutes": round(curr_time, 2),
                "fare_rupees": seg_fare,
                "distance_m": round(curr_distance_m, 1),
                "intermediate_stops": inter_stops,
                "all_stops": all_step_stops
            })
            curr = next_hop.copy()
            curr_stop_count = 1
            curr_from_id = curr["from_id"]
            curr_from_name = curr["from_name"]
            curr_time = curr["travel_time"]
            curr_distance_m = curr.get("distance_m", 0.0)
            curr_stops_sequence = [curr["from_id"], curr["to_id"]]

    final_fare = calculate_segment_fare(curr["mode"], curr_stop_count, curr_distance_m) if curr["edge_type"] != "transfer" else 0.0
    from_info = stop_lookup.get(curr_from_id, {})
    to_info = stop_lookup.get(curr["to_id"], {})

    inter_stops = [
        {
            "stop_id": sid,
            "stop_name": stop_lookup[sid]["stop_name"],
            "lat": stop_lookup[sid].get("lat"),
            "lng": stop_lookup[sid].get("lng")
        }
        for sid in curr_stops_sequence[1:-1]
        if sid in stop_lookup
    ]
    all_step_stops = [
        {
            "stop_id": sid,
            "stop_name": stop_lookup[sid]["stop_name"],
            "lat": stop_lookup[sid].get("lat"),
            "lng": stop_lookup[sid].get("lng")
        }
        for sid in curr_stops_sequence
        if sid in stop_lookup
    ]

    steps.append({
        "mode": curr["mode"],
        "line_id": curr["line_id"],
        "edge_type": curr["edge_type"],
        "from_stop": curr_from_name,
        "from_id": curr_from_id,
        "from_lat": from_info.get("lat"),
        "from_lng": from_info.get("lng"),
        "to_stop": curr["to_name"],
        "to_id": curr["to_id"],
        "to_lat": to_info.get("lat"),
        "to_lng": to_info.get("lng"),
        "stop_count": curr_stop_count if curr["edge_type"] != "transfer" else 0,
        "time_minutes": round(curr_time, 2),
        "fare_rupees": final_fare,
        "distance_m": round(curr_distance_m, 1),
        "intermediate_stops": inter_stops,
        "all_stops": all_step_stops
    })

    # Filter out redundant self-transfer steps (0-distance or identical stop names)
    filtered_steps = []
    for s in steps:
        if s["edge_type"] == "transfer":
            if s["from_id"] == s["to_id"] or (s["from_stop"] == s["to_stop"] and s["distance_m"] < 5.0):
                continue
        filtered_steps.append(s)
    steps = filtered_steps

    # Re-align Metro fares across continuous Metro segments for single-token pricing
    i = 0
    while i < len(steps):
        if steps[i]["mode"] == "metro":
            j = i
            metro_indices = []
            while j < len(steps):
                if steps[j]["mode"] == "metro":
                    metro_indices.append(j)
                    j += 1
                elif steps[j]["edge_type"] == "transfer" and j + 1 < len(steps) and steps[j + 1]["mode"] == "metro":
                    j += 1
                else:
                    break

            if len(metro_indices) > 1:
                total_metro_dist_m = sum(steps[idx]["distance_m"] for idx in metro_indices)
                total_metro_fare = calculate_metro_fare(total_metro_dist_m / 1000.0)

                accum_fare = 0.0
                for idx_pos, idx in enumerate(metro_indices):
                    if idx_pos == len(metro_indices) - 1:
                        steps[idx]["fare_rupees"] = round(total_metro_fare - accum_fare, 1)
                    else:
                        portion = round(total_metro_fare * (steps[idx]["distance_m"] / max(1.0, total_metro_dist_m)), 1)
                        steps[idx]["fare_rupees"] = portion
                        accum_fare += portion
            i = max(i + 1, j)
        else:
            i += 1

    # Calculate actual vehicle-to-vehicle transfer count
    transit_vehicle_legs = [s for s in steps if s["edge_type"] != "transfer"]
    num_transfers = max(0, len(transit_vehicle_legs) - 1)
    total_fare = sum(s["fare_rupees"] for s in steps)

    return steps, round(total_time, 1), round(total_fare, 1), num_transfers


def find_routes(
    graph=None,
    stop_lookup: dict = None,
    origin_name: str = "",
    destination_name: str = "",
    max_results: int = 3,
    allowed_modes: list[str] = None
) -> list[dict]:
    """
    Finds up to `max_results` distinct multi-modal route options between origin and destination.
    Accepts `allowed_modes` (list of str e.g. ["bus", "metro", "mmts"]) to filter vehicle graph traversal.
    Returns list of dicts with steps, total_time_minutes, total_fare_rupees, num_transfers, route_type.
    """
    if graph is None or stop_lookup is None:
        graph, stop_lookup = load_graph_and_lookup()
    elif isinstance(graph, str):
        graph, stop_lookup = load_graph_and_lookup(pickle_path=graph)

    # 0. Mode filtering setup (always allow walking transfer edges between stops)
    if allowed_modes is None or not allowed_modes:
        allowed_modes_set = {"bus", "metro", "mmts", "walk"}
    else:
        allowed_modes_set = {str(m).strip().lower() for m in allowed_modes}
        allowed_modes_set.add("walk")

    def is_edge_allowed(u, v):
        edge = graph[u][v]
        edge_type = edge.get("type", "")
        edge_mode = str(edge.get("mode", "")).strip().lower()
        if edge_type == "transfer" or edge_mode == "walk":
            return True
        return edge_mode in allowed_modes_set

    search_graph = nx.subgraph_view(graph, filter_edge=is_edge_allowed)

    # 1. Validation: Same origin and destination check
    if origin_name.strip().lower() == destination_name.strip().lower():
        raise ValueError("Origin and destination cannot be the same stop. Please select two different stations.")

    # 2. Validation & Resolution: Origin stop matching
    origin_ids = resolve_stop(origin_name, stop_lookup)
    if not origin_ids:
        closest = get_closest_stop_names(origin_name, stop_lookup, n=3)
        closest_str = ", ".join(closest)
        raise ValueError(f"Stop not found — did you mean: {closest_str}?")

    # 3. Validation & Resolution: Destination stop matching
    dest_ids = resolve_stop(destination_name, stop_lookup)
    if not dest_ids:
        closest = get_closest_stop_names(destination_name, stop_lookup, n=3)
        closest_str = ", ".join(closest)
        raise ValueError(f"Stop not found — did you mean: {closest_str}?")

    # 4. Check if resolved stop IDs are identical
    if set(origin_ids) == set(dest_ids):
        resolved_name = stop_lookup[origin_ids[0]]["stop_name"]
        raise ValueError(f"Origin and destination resolve to the same stop ('{resolved_name}'). Please select two different stations.")

    # DEBUG: Print resolved origin and destination IDs for diagnosis
    print(f"[DEBUG find_routes] Origin '{origin_name}' resolved to IDs: {origin_ids} ({[stop_lookup[i]['stop_name'] for i in origin_ids]})")
    print(f"[DEBUG find_routes] Destination '{destination_name}' resolved to IDs: {dest_ids} ({[stop_lookup[i]['stop_name'] for i in dest_ids]})")

    raw_candidates = []
    seen_route_signatures = set()

    # Define weight functions for multi-objective diversity search (with transfer penalties to minimize walking hops)
    search_objectives = [
        lambda u, v, d: d.get("travel_time", 1.0) + (15.0 if d.get("type") == "transfer" else 0.0),
        lambda u, v, d: d.get("fare", 1.0) + 0.1 * d.get("travel_time", 1.0) + (15.0 if d.get("type") == "transfer" else 0.0),
        lambda u, v, d: d.get("travel_time", 1.0) + (45.0 if d.get("type") == "transfer" else 0.0)
    ]

    for weight_fn in search_objectives:
        best_path = None
        best_weight = float("inf")

        for orig in origin_ids:
            for dest in dest_ids:
                if orig == dest:
                    continue
                try:
                    path = nx.dijkstra_path(search_graph, orig, dest, weight=weight_fn)
                    path_weight = nx.dijkstra_path_length(search_graph, orig, dest, weight=weight_fn)
                    if path_weight < best_weight:
                        best_weight = path_weight
                        best_path = path
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

        if best_path:
            steps, t_time, t_fare, n_transfers = parse_path_to_steps(graph, best_path, stop_lookup)
            step_sig = tuple((s["mode"], s["from_id"], s["to_id"]) for s in steps)
            route_sig = (round(t_time, 1), round(t_fare, 1), n_transfers, step_sig)

            if route_sig not in seen_route_signatures:
                seen_route_signatures.add(route_sig)
                is_accessible = all(stop_lookup.get(nid, {}).get("is_accessible", False) for nid in best_path)
                raw_candidates.append({
                    "origin": stop_lookup[best_path[0]]["stop_name"],
                    "destination": stop_lookup[best_path[-1]]["stop_name"],
                    "total_time_minutes": t_time,
                    "total_fare_rupees": t_fare,
                    "num_transfers": n_transfers,
                    "is_accessible": is_accessible,
                    "steps": steps,
                    "node_path": best_path
                })

    # If we need more routes to reach max_results, use Yen's k-shortest paths on travel_time
    if len(raw_candidates) < max_results + 3:
        for orig in origin_ids:
            for dest in dest_ids:
                if orig == dest:
                    continue
                try:
                    path_gen = nx.shortest_simple_paths(search_graph, orig, dest, weight="travel_time")
                    for path in itertools.islice(path_gen, 7):
                        steps, t_time, t_fare, n_transfers = parse_path_to_steps(graph, path, stop_lookup)
                        step_sig = tuple((s["mode"], s["from_id"], s["to_id"]) for s in steps)
                        route_sig = (round(t_time, 1), round(t_fare, 1), n_transfers, step_sig)
                        if route_sig not in seen_route_signatures:
                            seen_route_signatures.add(route_sig)
                            is_accessible = all(stop_lookup.get(nid, {}).get("is_accessible", False) for nid in path)
                            raw_candidates.append({
                                "origin": stop_lookup[path[0]]["stop_name"],
                                "destination": stop_lookup[path[-1]]["stop_name"],
                                "total_time_minutes": t_time,
                                "total_fare_rupees": t_fare,
                                "num_transfers": n_transfers,
                                "is_accessible": is_accessible,
                                "steps": steps,
                                "node_path": path
                            })
                        if len(raw_candidates) >= max_results + 5:
                            break
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue
                if len(raw_candidates) >= max_results + 5:
                    break
            if len(raw_candidates) >= max_results + 5:
                break

    if not raw_candidates:
        active_vehicle_modes = [m for m in ["bus", "metro", "mmts"] if m in allowed_modes_set]
        if len(active_vehicle_modes) < 3:
            mode_display_map = {"bus": "Bus", "metro": "Metro", "mmts": "MMTS"}
            modes_str = ", ".join(mode_display_map[m] for m in active_vehicle_modes) if active_vehicle_modes else "selected"
            raise ValueError(f"No route found using only {modes_str} — try enabling more transport modes.")
        return []

    # Dynamic Category Label Assignment based on actual computed metrics
    # 1. Cheapest: lowest total_fare_rupees
    cheapest_candidate = min(
        raw_candidates,
        key=lambda r: (r["total_fare_rupees"], r["total_time_minutes"], r["num_transfers"])
    )

    # 2. Fastest: lowest total_time_minutes
    fastest_candidate = min(
        raw_candidates,
        key=lambda r: (r["total_time_minutes"], r["total_fare_rupees"], r["num_transfers"])
    )

    # 3. Fewest Transfers: lowest num_transfers
    fewest_transfers_candidate = min(
        raw_candidates,
        key=lambda r: (r["num_transfers"], r["total_time_minutes"], r["total_fare_rupees"])
    )

    category_winners = []
    other_candidates = []

    for route in raw_candidates:
        labels = []
        if route is fastest_candidate:
            labels.append("Fastest")
        if route is cheapest_candidate:
            labels.append("Cheapest")
        if route is fewest_transfers_candidate:
            labels.append("Fewest Transfers")

        route_copy = route.copy()
        if labels:
            if len(labels) == 1:
                route_copy["route_type"] = labels[0]
            elif len(labels) == 2:
                route_copy["route_type"] = f"{labels[0]} & {labels[1]}"
            else:
                route_copy["route_type"] = f"{labels[0]}, {labels[1]} & {labels[2]}"
            category_winners.append(route_copy)
        else:
            other_candidates.append(route_copy)

    # Sort category winners: Fastest winner first, then Cheapest winner, then Fewest Transfers winner
    ordered_winners = []
    for r in category_winners:
        if "Fastest" in r["route_type"] and r not in ordered_winners:
            ordered_winners.append(r)
    for r in category_winners:
        if "Cheapest" in r["route_type"] and r not in ordered_winners:
            ordered_winners.append(r)
    for r in category_winners:
        if "Fewest Transfers" in r["route_type"] and r not in ordered_winners:
            ordered_winners.append(r)
    for r in category_winners:
        if r not in ordered_winners:
            ordered_winners.append(r)

    # Assign labels to remaining alternative routes
    alt_index = 1
    for r in other_candidates:
        r["route_type"] = f"Alternative {alt_index}"
        alt_index += 1

    final_routes = ordered_winners + other_candidates
    return final_routes[:max_results]


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    # Self-test demonstration when run directly
    print("Testing find_routes module...")
    G, lookup = load_graph_and_lookup()
    res = find_routes(G, lookup, "HITEC City", "LB Nagar")
    print(f"Found {len(res)} routes for HITEC City -> LB Nagar.")
    for r in res:
        print(f"\n[{r['route_type']}] Time: {r['total_time_minutes']}m | Fare: ₹{r['total_fare_rupees']} | Transfers: {r['num_transfers']}")
        for s in r["steps"]:
            print(f"  • {s['mode'].upper()} ({s['line_id']}): {s['from_stop']} -> {s['to_stop']} ({s['time_minutes']} min, ₹{s['fare_rupees']})")
