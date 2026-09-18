import json

# Original Bus Corridor 216
bus_stops = [
    {"stop_id": "bus_gachi_sec_00", "stop_name": "Gachibowli X Roads", "lat": 17.4401, "lng": 78.3489, "mode": "bus", "line_id": "route_216", "sequence": 0, "is_accessible": True},
    {"stop_id": "bus_gachi_sec_01", "stop_name": "Bio-Diversity Park", "lat": 17.4435, "lng": 78.3653, "mode": "bus", "line_id": "route_216", "sequence": 1, "is_accessible": False},
    {"stop_id": "bus_gachi_sec_02", "stop_name": "Raidurg Bus Stop", "lat": 17.4423, "lng": 78.3772, "mode": "bus", "line_id": "route_216", "sequence": 2, "is_accessible": False},
    {"stop_id": "bus_gachi_sec_03", "stop_name": "Madhapur Police Station", "lat": 17.4485, "lng": 78.3908, "mode": "bus", "line_id": "route_216", "sequence": 3, "is_accessible": True},
    {"stop_id": "bus_gachi_sec_04", "stop_name": "Jubilee Hills Check Post", "lat": 17.4350, "lng": 78.4116, "mode": "bus", "line_id": "route_216", "sequence": 4, "is_accessible": False},
    {"stop_id": "bus_gachi_sec_05", "stop_name": "Punjagutta Bus Stop", "lat": 17.4256, "lng": 78.4518, "mode": "bus", "line_id": "route_216", "sequence": 5, "is_accessible": False},
    {"stop_id": "bus_gachi_sec_06", "stop_name": "Begumpet Bus Stop", "lat": 17.4447, "lng": 78.4662, "mode": "bus", "line_id": "route_216", "sequence": 6, "is_accessible": False},
    {"stop_id": "bus_gachi_sec_07", "stop_name": "Paradise Circle", "lat": 17.4415, "lng": 78.4872, "mode": "bus", "line_id": "route_216", "sequence": 7, "is_accessible": True},
    {"stop_id": "bus_gachi_sec_08", "stop_name": "Patny Center", "lat": 17.4428, "lng": 78.4965, "mode": "bus", "line_id": "route_216", "sequence": 8, "is_accessible": True},
    {"stop_id": "bus_gachi_sec_09", "stop_name": "Secunderabad Station Bus Stand", "lat": 17.4339, "lng": 78.5016, "mode": "bus", "line_id": "route_216", "sequence": 9, "is_accessible": True}
]

# 1. Metro Red Line (Miyapur -> LB Nagar) - 27 Stations
metro_red = [
    ("Miyapur Metro Station", 17.4968, 78.3614),
    ("JNTU College Metro Station", 17.4965, 78.3892),
    ("KPHB Colony Metro Station", 17.4932, 78.3998),
    ("Kukatpally Metro Station", 17.4842, 78.4101),
    ("Balanagar Metro Station", 17.4722, 78.4215),
    ("Moosapet Metro Station", 17.4682, 78.4251),
    ("Bharat Nagar Metro Station", 17.4640, 78.4278),
    ("Erragadda Metro Station", 17.4561, 78.4385),
    ("ESI Hospital Metro Station", 17.4485, 78.4425),
    ("SR Nagar Metro Station", 17.4418, 78.4482),
    ("Ameerpet Metro Station", 17.4357, 78.4446),
    ("Punjagutta Metro Station", 17.4256, 78.4518),
    ("Irrum Manzil Metro Station", 17.4206, 78.4568),
    ("Khairatabad Metro Station", 17.4124, 78.4608),
    ("Lakdikapul Metro Station", 17.4048, 78.4632),
    ("Assembly Metro Station", 17.3976, 78.4695),
    ("Nampally Metro Station", 17.3912, 78.4715),
    ("Gandhi Bhavan Metro Station", 17.3854, 78.4752),
    ("Osmania Medical College Metro Station", 17.3802, 78.4795),
    ("MGBS Metro Station", 17.3789, 78.4812),
    ("Malakpet Metro Station", 17.3745, 78.4952),
    ("New Market Metro Station", 17.3712, 78.5065),
    ("Musarambagh Metro Station", 17.3695, 78.5142),
    ("Dilsukhnagar Metro Station", 17.3688, 78.5247),
    ("Chaitanyapuri Metro Station", 17.3621, 78.5345),
    ("Victoria Memorial Metro Station", 17.3582, 78.5412),
    ("LB Nagar Metro Station", 17.3522, 78.5484)
]

# 2. Metro Blue Line (Raidurg -> Nagole) - 23 Stations
metro_blue = [
    ("Raidurg Metro Station", 17.4423, 78.3772),
    ("HITEC City Metro Station", 17.4489, 78.3831),
    ("Durgam Cheruvu Metro Station", 17.4429, 78.3934),
    ("Madhapur Metro Station", 17.4402, 78.3995),
    ("Peddamma Gudi Metro Station", 17.4372, 78.4055),
    ("Jubilee Hills Check Post Metro Station", 17.4350, 78.4116),
    ("Road No 5 Jubilee Hills Metro Station", 17.4340, 78.4230),
    ("Yusufguda Metro Station", 17.4335, 78.4320),
    ("Madhura Nagar Metro Station", 17.4348, 78.4395),
    ("Ameerpet Metro Station", 17.4357, 78.4446),
    ("Begumpet Metro Station", 17.4442, 78.4665),
    ("Prakash Nagar Metro Station", 17.4435, 78.4755),
    ("Rasoolpura Metro Station", 17.4430, 78.4820),
    ("Paradise Metro Station", 17.4415, 78.4872),
    ("JBS Parade Ground Metro Station", 17.4448, 78.4982),
    ("Secunderabad East Metro Station", 17.4353, 78.5019),
    ("Mettuguda Metro Station", 17.4312, 78.5175),
    ("Tarnaka Metro Station", 17.4278, 78.5312),
    ("Habsiguda Metro Station", 17.4195, 78.5425),
    ("NGRI Metro Station", 17.4085, 78.5510),
    ("Stadium Metro Station", 17.4022, 78.5585),
    ("Uppal Metro Station", 17.3985, 78.5642),
    ("Nagole Metro Station", 17.3785, 78.5665)
]

# 3. Metro Green Line (JBS Parade Ground -> MGBS) - 9 Stations
metro_green = [
    ("JBS Parade Ground Metro Station", 17.4448, 78.4982),
    ("Secunderabad West Metro Station", 17.4345, 78.5002),
    ("Gandhi Hospital Metro Station", 17.4252, 78.5035),
    ("Musheerabad Metro Station", 17.4168, 78.5020),
    ("RTC X Roads Metro Station", 17.4082, 78.4985),
    ("Chikkadpally Metro Station", 17.4005, 78.4952),
    ("Narayanguda Metro Station", 17.3915, 78.4895),
    ("Sultan Bazaar Metro Station", 17.3845, 78.4842),
    ("MGBS Metro Station", 17.3789, 78.4812)
]

# 4. MMTS Lines
# Line 1: Falaknuma to Lingampally (FL/HF line - 22 stops)
mmts_flp = [
    ("Falaknuma Railway Station", 17.3372, 78.4754),
    ("Uppuguda Railway Station", 17.3485, 78.4812),
    ("Yakutpura Railway Station", 17.3592, 78.4868),
    ("Dabirpura Railway Station", 17.3668, 78.4912),
    ("Malakpet MMTS Station", 17.3731, 78.4942),
    ("Kacheguda Railway Station", 17.3842, 78.4951),
    ("Vidyanagar Railway Station", 17.3996, 78.5028),
    ("Jamai Osmania Railway Station", 17.4082, 78.5065),
    ("Arts College Railway Station", 17.4145, 78.5085),
    ("Sitafalmandi Railway Station", 17.4208, 78.5106),
    ("Secunderabad Junction Railway Station", 17.4353, 78.5019),
    ("James Street Railway Station", 17.4362, 78.4892),
    ("Sanjeevaiah Park Railway Station", 17.4348, 78.4785),
    ("Begumpet Railway Station", 17.4442, 78.4665),
    ("Nature Cure Hospital Railway Station", 17.4525, 78.4485),
    ("Fateh Nagar Railway Station", 17.4582, 78.4395),
    ("Bharat Nagar MMTS Station", 17.4638, 78.4276),
    ("Borabanda Railway Station", 17.4628, 78.4112),
    ("Hi-Tech City MMTS Station", 17.4645, 78.3842),
    ("Hafizpet Railway Station", 17.4795, 78.3582),
    ("Chanda Nagar Railway Station", 17.4810, 78.3392),
    ("Lingampally Railway Station", 17.4813, 78.3184)
]

# Line 2: Secunderabad to Bolarum / Medchal (11 stops)
mmts_sb = [
    ("Secunderabad Junction Railway Station", 17.4353, 78.5019),
    ("Lallaguda Railway Station", 17.4395, 78.5142),
    ("Malkajgiri Railway Station", 17.4482, 78.5285),
    ("Dayanand Nagar Railway Station", 17.4565, 78.5312),
    ("Safilguda Railway Station", 17.4632, 78.5345),
    ("Ramakistapuram Gate Railway Station", 17.4752, 78.5398),
    ("Ammuguda Railway Station", 17.4842, 78.5422),
    ("Cavalry Barracks Railway Station", 17.4935, 78.5385),
    ("Alwal Railway Station", 17.5028, 78.5320),
    ("Bolarum Railway Station", 17.5255, 78.5145),
    ("Medchal Railway Station", 17.6285, 78.4812)
]

# Line 3: Falaknuma to Umdanagar (4 stops)
mmts_fu = [
    ("Falaknuma Railway Station", 17.3372, 78.4754),
    ("Engine Bowli Railway Station", 17.3210, 78.4712),
    ("Budvel Railway Station", 17.3085, 78.4312),
    ("Umdanagar Railway Station", 17.2512, 78.4285)
]

# Line 4: Secunderabad to Nampally (7 stops)
mmts_sh = [
    ("Secunderabad Junction Railway Station", 17.4353, 78.5019),
    ("James Street Railway Station", 17.4362, 78.4892),
    ("Sanjeevaiah Park Railway Station", 17.4348, 78.4785),
    ("Begumpet Railway Station", 17.4442, 78.4665),
    ("Khairatabad Railway Station", 17.4120, 78.4605),
    ("Lakdikapul Railway Station", 17.4045, 78.4630),
    ("Hyderabad Nampally Railway Station", 17.3915, 78.4712)
]

stops_list = []
stops_list.extend(bus_stops)

# Helper to add line stops
def add_metro_line(stations, line_id, prefix):
    for seq, (name, lat, lng) in enumerate(stations):
        stops_list.append({
            "stop_id": f"{prefix}_{seq:02d}",
            "stop_name": name,
            "lat": lat,
            "lng": lng,
            "mode": "metro",
            "line_id": line_id,
            "sequence": seq,
            "is_accessible": True
        })

def add_mmts_line(stations, line_id, prefix):
    for seq, (name, lat, lng) in enumerate(stations):
        stops_list.append({
            "stop_id": f"{prefix}_{seq:02d}",
            "stop_name": name,
            "lat": lat,
            "lng": lng,
            "mode": "mmts",
            "line_id": line_id,
            "sequence": seq,
            "is_accessible": True
        })

add_metro_line(metro_red, "red_line", "metro_red")
add_metro_line(metro_blue, "blue_line", "metro_blue")
add_metro_line(metro_green, "green_line", "metro_green")

add_mmts_line(mmts_flp, "mmts_falaknuma_lingampally", "mmts_flp")
add_mmts_line(mmts_sb, "mmts_secunderabad_bolarum", "mmts_sb")
add_mmts_line(mmts_fu, "mmts_falaknuma_umdanagar", "mmts_fu")
add_mmts_line(mmts_sh, "mmts_secunderabad_hyderabad", "mmts_sh")

with open("stops.json", "w", encoding="utf-8") as f:
    json.dump({"stops": stops_list}, f, indent=2, ensure_ascii=False)

print(f"Successfully generated stops.json with {len(stops_list)} total stop entries.")
