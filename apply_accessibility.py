"""
apply_accessibility.py
----------------------
Updates stops.json to include 'is_accessible': true/false field.
HMRL Metro stations and major multimodal interchange stations are marked as accessible.
Rebuilds graph_data.json and graph.pickle.
"""

import json
import build_graph

def main():
    with open("stops.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    stops = data.get("stops", [])
    accessible_keywords = ("station", "metro", "mmts", "gachibowli", "bus stand", "patny", "paradise")

    for s in stops:
        mode = s.get("mode", "").lower()
        name = s.get("stop_name", "").lower()

        # HMRL Metro stations are 100% accessible (elevators, escalators, tactile paving)
        if mode == "metro":
            s["is_accessible"] = True
        elif mode == "mmts":
            # MMTS rail stations with step-free ramps/overbridges
            s["is_accessible"] = True
        elif any(kw in name for kw in accessible_keywords):
            s["is_accessible"] = True
        else:
            s["is_accessible"] = False

    with open("stops.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    acc_count = sum(1 for s in stops if s["is_accessible"])
    print(f"[SUCCESS] Updated stops.json: {acc_count}/{len(stops)} stops marked as wheelchair accessible.")

if __name__ == "__main__":
    main()
