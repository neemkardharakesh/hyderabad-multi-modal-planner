# Run: python app.py, then open index.html
"""
app.py
------
Flask REST API server for Hyderabad Multi-Modal Journey Planner.
Exposes routes for route planning and stop name autocomplete.

Endpoints:
  POST /api/find_routes - Finds optimal multi-modal routes and AI recommendation
  GET  /api/stops       - Returns list of available transit stops for UI autocomplete
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

from find_routes import find_routes, load_graph_and_lookup
from recommend_route import recommend_route, CONTEXT_PROFILES

app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app)  # Enable Cross-Origin Resource Sharing for frontend web app

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')


# Pre-load graph and stop lookup map on app startup
try:
    G, STOP_LOOKUP = load_graph_and_lookup("graph.pickle", "graph_data.json")
    print(f"[INFO] Graph loaded successfully with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
except Exception as e:
    print(f"[ERROR] Failed to load graph: {e}")
    G, STOP_LOOKUP = None, {}


@app.route("/api/stops", methods=["GET"])
def get_stops():
    """Returns list of available transit stop names for autocomplete and validation."""
    if not STOP_LOOKUP:
        return jsonify({"status": "error", "message": "Graph data not loaded"}), 500

    # Collect unique stop names sorted alphabetically
    unique_names = sorted(list(set(info["stop_name"] for info in STOP_LOOKUP.values())))
    stops_detail = [
        {
            "stop_id": info["stop_id"],
            "stop_name": info["stop_name"],
            "mode": info["mode"],
            "line_id": info["line_id"],
            "lat": info.get("lat"),
            "lng": info.get("lng")
        }
        for info in STOP_LOOKUP.values()
    ]

    return jsonify({
        "status": "success",
        "names": unique_names,
        "stops": stops_detail
    })


@app.route("/api/find_routes", methods=["POST"])
def api_find_routes():
    """
    Accepts JSON body: {"origin": str, "destination": str, "context": "peak|off_peak|budget"}
    Returns candidate routes, component score breakdown, and AI recommendation.
    """
    if not G or not STOP_LOOKUP:
        return jsonify({"status": "error", "message": "Graph data not initialized. Run build_graph.py first."}), 500

    data = request.get_json(silent=True) or {}
    origin = data.get("origin", "").strip()
    destination = data.get("destination", "").strip()
    context = data.get("context", "off_peak").strip().lower()
    allowed_modes = data.get("allowed_modes", ["bus", "metro", "mmts"])
    if not isinstance(allowed_modes, list) or not allowed_modes:
        allowed_modes = ["bus", "metro", "mmts"]

    if not origin or not destination:
        return jsonify({
            "status": "error",
            "message": "Both 'origin' and 'destination' fields are required."
        }), 400

    if context not in CONTEXT_PROFILES:
        context = "off_peak"

    try:
        candidate_routes = find_routes(
            graph=G,
            stop_lookup=STOP_LOOKUP,
            origin_name=origin,
            destination_name=destination,
            max_results=3,
            allowed_modes=allowed_modes
        )

        if not candidate_routes:
            active_modes = [m for m in ["bus", "metro", "mmts"] if m in [x.lower() for x in allowed_modes]]
            if len(active_modes) < 3:
                mode_display_map = {"bus": "Bus", "metro": "Metro", "mmts": "MMTS"}
                modes_str = ", ".join(mode_display_map[m] for m in active_modes) if active_modes else "selected"
                msg = f"No route found using only {modes_str} — try enabling more transport modes."
            else:
                msg = f"No valid transit path found between '{origin}' and '{destination}'."
            return jsonify({
                "status": "error",
                "message": msg
            }), 404

        # Run multi-attribute recommendation engine
        rec_route, reason, scored_routes = recommend_route(candidate_routes, context=context)

        return jsonify({
            "status": "success",
            "origin": origin,
            "destination": destination,
            "context": context,
            "context_info": CONTEXT_PROFILES[context],
            "recommended_route": rec_route,
            "recommendation_reason": reason,
            "routes": scored_routes
        })

    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server routing error: {str(e)}"}), 500


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("==================================================================")
    print("      HYDERABAD MULTI-MODAL ROUTE PLANNER API SERVER")
    print("==================================================================")
    print("Starting Flask API server on http://localhost:5000 ...\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
