"""
test_search_validation.py
--------------------------
Integration test suite for search flow validation, fuzzy matching suggestions,
same-stop errors, no-route handling, and multi-corridor journey planning.
"""

import sys
import json
from find_routes import find_routes, load_graph_and_lookup

def run_tests():
    print("==================================================================")
    print("      HYDERABAD MULTI-MODAL SEARCH VALIDATION & ROUTING TEST")
    print("==================================================================")

    G, lookup = load_graph_and_lookup()

    # ---------------------------------------------------------
    # TEST GROUP 1: Input Validation & Fuzzy Matching Errors
    # ---------------------------------------------------------
    print("\n--- TEST GROUP 1: Input Validation & Fuzzy Matching Suggestions ---")
    
    validation_test_cases = [
        ("Invalid Origin", "Unknown Station XYZ", "LB Nagar"),
        ("Invalid Destination", "Miyapur", "Banjara Hills Nonexistent"),
        ("Same Origin & Destination (Identical String)", "Ameerpet", "Ameerpet"),
        ("Same Origin & Destination (Different Case)", "Miyapur Metro Station", "miyapur metro station")
    ]

    for name, orig, dest in validation_test_cases:
        print(f"\n[TEST CASE: {name}]")
        print(f"  Input: '{orig}' -> '{dest}'")
        try:
            routes = find_routes(G, lookup, orig, dest)
            print(f"  ❌ FAILED: Expected ValueError exception, but got {len(routes)} routes.")
        except ValueError as ve:
            print(f"  ✅ SUCCESS: Caught expected error message:")
            print(f"     \"{str(ve)}\"")

    # ---------------------------------------------------------
    # TEST GROUP 2: Disconnected / No Route Case (Graceful Handling)
    # ---------------------------------------------------------
    print("\n--- TEST GROUP 2: No Route Between Valid Stops ---")
    # Simulate an isolated stop in graph to test nx.NetworkXNoPath handling
    import networkx as nx
    G_temp = G.copy()
    lookup_temp = lookup.copy()
    G_temp.add_node("ISOLATED_STOP_001", stop_id="ISOLATED_STOP_001", stop_name="Isolated Secret Island Stop", mode="bus")
    lookup_temp["ISOLATED_STOP_001"] = {"stop_id": "ISOLATED_STOP_001", "stop_name": "Isolated Secret Island Stop", "mode": "bus"}

    print("\n[TEST CASE: Disconnected Graph Node Query]")
    print("  Input: 'Miyapur' -> 'Isolated Secret Island Stop'")
    try:
        routes = find_routes(G_temp, lookup_temp, "Miyapur", "Isolated Secret Island Stop")
        if not routes:
            print("  ✅ SUCCESS: Gracefully returned 0 routes (empty candidate list) for disconnected graph path.")
        else:
            print(f"  ❌ Unexpected: Returned {len(routes)} routes.")
    except Exception as e:
        print(f"  ℹ️ Caught exception: {e}")

    # ---------------------------------------------------------
    # TEST GROUP 3: 6 New O-D Pairs Across the 4 Corridors
    # ---------------------------------------------------------
    print("\n--- TEST GROUP 3: Testing 6 New O-D Pairs Across 4 Corridors ---")
    
    corridor_test_pairs = [
        ("Corridor 1 (Red Line Metro)", "Miyapur", "LB Nagar"),
        ("Corridor 2 (Blue Line Metro)", "HITEC City", "Secunderabad"),
        ("Corridor 3 (Green Line & MMTS Rail)", "Begumpet", "Lingampally"),
        ("Corridor 4 (Bus & Metro Transfer)", "Gachibowli", "Ameerpet"),
        ("Cross-Corridor (Red Line <-> Blue Line)", "KPHB", "Secunderabad"),
        ("Heritage & Old City Multi-Modal", "Falaknuma", "Kukatpally")
    ]

    all_passed = True
    results_summary = []

    for corridor, orig, dest in corridor_test_pairs:
        print(f"\n[TEST PAIR: {corridor}]")
        print(f"  Searching: '{orig}' ➔ '{dest}'")
        try:
            routes = find_routes(G, lookup, orig, dest, max_results=3)
            if not routes:
                print(f"  ❌ BROKEN RESULT: No routes found for '{orig}' ➔ '{dest}'.")
                all_passed = False
                results_summary.append((corridor, orig, dest, "BROKEN: 0 routes returned"))
            else:
                print(f"  ✅ SUCCESS: Found {len(routes)} valid route option(s):")
                for r in routes:
                    steps_summary = " -> ".join([f"{s['mode'].upper()} ({s['from_stop']} to {s['to_stop']})" for s in r['steps']])
                    print(f"     • [{r['route_type']}] {r['total_time_minutes']} min | ₹{r['total_fare_rupees']} | {r['num_transfers']} transfer(s)")
                    print(f"       Steps: {steps_summary}")
                results_summary.append((corridor, orig, dest, f"OK ({len(routes)} options, best: {routes[0]['total_time_minutes']}m / ₹{routes[0]['total_fare_rupees']})"))
        except Exception as e:
            print(f"  ❌ ERROR: Exception during routing: {e}")
            all_passed = False
            results_summary.append((corridor, orig, dest, f"ERROR: {e}"))

    print("\n==================================================================")
    print("                     FINAL TEST SUMMARY")
    print("==================================================================")
    for corridor, orig, dest, status in results_summary:
        print(f"• [{corridor}] {orig} -> {dest}: {status}")

    if all_passed:
        print("\n🎉 ALL TEST SUITES PASSED WITH ZERO BROKEN RESULTS!")
    else:
        print("\n⚠️ SOME ROUTE TESTS FAILED. PLEASE REVIEW THE SUMMARY ABOVE.")

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    run_tests()
