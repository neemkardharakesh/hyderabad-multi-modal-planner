"""
test_planner.py
---------------
Test suite for the Hyderabad multi-modal journey planner.
Evaluates 3 key test trips across Bus, Metro, and MMTS networks:
1. Gachibowli → Secunderabad Station
2. HITEC City → LB Nagar (tests Ameerpet interchange between Red & Blue lines)
3. Begumpet → Lingampally (tests Bus → MMTS transfer)

Integrates on-device route recommendation engine (recommend_route.py).
"""

import sys
import os
from find_routes import find_routes, load_graph_and_lookup
from recommend_route import recommend_route, CONTEXT_PROFILES


def format_summary_path(route: dict) -> str:
    """Creates a concise single-line summary string like: Gachibowli --[bus]--> ... --[walk]--> Begumpet"""
    steps = route["steps"]
    if not steps:
        return f"{route['origin']} -> {route['destination']}"

    parts = [steps[0]["from_stop"]]
    for s in steps:
        mode_label = s["mode"]
        line_info = f"{mode_label} ({s['line_id']})" if s['edge_type'] != 'transfer' else "walk"
        parts.append(f"--[{line_info}]--> {s['to_stop']}")

    return " ".join(parts)


def run_test_planner():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=================================================================================")
    print("           HYDERABAD MULTI-MODAL JOURNEY PLANNER TEST SUITE")
    print("=================================================================================\n")

    # Load graph and stop lookup table
    G, stop_lookup = load_graph_and_lookup("graph.pickle", "graph_data.json")

    test_trips = [
        {
            "title": "TRIP 1: Gachibowli → Secunderabad Station",
            "origin": "Gachibowli",
            "destination": "Secunderabad",
            "notes": "Tests direct bus vs bus+MMTS transfer route options.",
            "demo_context": "peak"
        },
        {
            "title": "TRIP 2: HITEC City → LB Nagar",
            "origin": "HITEC City",
            "destination": "LB Nagar",
            "notes": "Tests Ameerpet interchange connection between Red Line and Blue Line.",
            "demo_context": "peak"
        },
        {
            "title": "TRIP 3: Begumpet → Lingampally",
            "origin": "Begumpet",
            "destination": "Lingampally",
            "notes": "Tests Bus to MMTS walking transfer connection.",
            "demo_context": "off_peak"
        },
        {
            "title": "TRIP 4: JNTU College → Nagole",
            "origin": "JNTU College",
            "destination": "Nagole",
            "notes": "Tests expanded Red Line to Blue Line metro transfer at Ameerpet.",
            "demo_context": "off_peak"
        },
        {
            "title": "TRIP 5: JBS Parade Ground → MGBS",
            "origin": "JBS Parade Ground",
            "destination": "MGBS",
            "notes": "Tests newly added Green Line Metro corridor.",
            "demo_context": "budget"
        },
        {
            "title": "TRIP 6: Bolarum → Umdanagar",
            "origin": "Bolarum",
            "destination": "Umdanagar",
            "notes": "Tests expanded MMTS lines (Secunderabad-Bolarum & Falaknuma-Umdanagar).",
            "demo_context": "off_peak"
        }
    ]

    for trip in test_trips:
        ctx_key = trip.get("demo_context", "peak")
        ctx_info = CONTEXT_PROFILES.get(ctx_key, CONTEXT_PROFILES["peak"])

        print(f"=================================================================================")
        print(f" {trip['title']}")
        print(f" Context Mode: {ctx_info['name']}")
        print(f" Description : {trip['notes']}")
        print(f"=================================================================================")

        try:
            routes = find_routes(
                graph=G,
                stop_lookup=stop_lookup,
                origin_name=trip["origin"],
                destination_name=trip["destination"],
                max_results=3
            )

            if not routes:
                print(f"[NO ROUTE FOUND] No valid path between '{trip['origin']}' and '{trip['destination']}'.\n")
                continue

            # Run route recommendation scoring engine
            rec_route, rec_reason, scored_routes = recommend_route(routes, context=ctx_key)

            print(f"\n[★ SMART RECOMMENDATION]")
            print(f"  ➜ {rec_reason}")
            print(f"  ➜ Best Choice: Route [{rec_route['route_type']}]\n")

            print("Available Candidate Route Options:")
            print("=" * 80)

            for idx, r in enumerate(scored_routes, 1):
                is_rec = " [★ RECOMMENDED]" if r["route_type"] == rec_route["route_type"] else ""
                summary_line = format_summary_path(r)
                print(f"Route {idx} ({r['route_type']}){is_rec}: {summary_line}")
                print(f"Time: {r['total_time_minutes']} min | Fare: ₹{r['total_fare_rupees']} | Transfers: {r['num_transfers']}")
                print("-" * 80)

                for s_idx, s in enumerate(r["steps"], 1):
                    if s["edge_type"] == "transfer":
                        print(f"  Step {s_idx}: Walk transfer from [{s['from_stop']}] to [{s['to_stop']}] (~{s['distance_m']}m, {s['time_minutes']} min, ₹0)")
                    else:
                        print(f"  Step {s_idx}: Ride {s['mode'].upper()} ({s['line_id']}) from [{s['from_stop']}] to [{s['to_stop']}] ({s['stop_count']} stops, {s['time_minutes']} min, ₹{s['fare_rupees']})")

                print()

        except Exception as e:
            print(f"[ERROR] Failed to calculate route for '{trip['origin']}' to '{trip['destination']}': {e}\n")

        print("\n")


if __name__ == "__main__":
    run_test_planner()
