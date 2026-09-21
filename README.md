# 🚌🚇🚆 Go Hyderabad

### **One App. Every Mode. Smarter Commutes for Hyderabad.**

A unified multi-modal journey planner for Hyderabad's public transport — combining **TSRTC Buses**, **Metro Rail**, and **MMTS suburban rail** into a single app with AI-recommended routes, live journey planning, and one-tap ticketing.

---

## 🧩 The Problem

Hyderabad's public transport runs as **three disconnected systems** — TSRTC buses, Metro, and MMTS — each with its own app (or no app at all), no shared data, and no way to plan a journey across them. Commuters guess transfers, juggle multiple apps, or default to private cabs simply because coordinating public transport feels too uncertain.

## 💡 The Solution

**Go Hyderabad** lets a user search a single origin and destination and get back route options that combine bus, metro, and rail — complete with walking transfers, fare estimates, and an 🤖 **AI-recommended "best" pick** — then book and pay in-app with a single 🎫 QR ticket generated at the end.

---

## ✨ Features

- 🗺️ **Multi-modal route planning** — Bus + Metro + MMTS combined into one search, with walking-transfer detection between nearby stops
- 🤖 **On-device AI recommendation** — a locally-run scikit-learn model scores every route option by time, fare, transfers, and crowding, with human-readable reasoning for its pick
- 📊 **Real official transit data** — built on HMRL Metro and TGSRTC Bus open GTFS feeds (**57 metro stations**, **1,031 bus routes**), not scraped or placeholder data
- 🧭 **Interactive live map** — Leaflet.js + OpenStreetMap route visualization with marker clustering for large datasets
- 🔐 **Real phone authentication** — Firebase Phone Auth (OTP-based login), not a mock
- 🎟️ **Single-ticket booking flow** — mock UPI-style payment → one QR ticket per journey, with support for multi-passenger group bookings
- 🌐 **Bilingual interface** — English, Telugu, and Hindi
- 🎙️ **Voice search** — speak an origin/destination using the Web Speech API
- ♿ **Accessibility filtering** — surfaces wheelchair-accessible stations and routes
- 📲 **Installable Progressive Web App** — add-to-home-screen support with offline-aware service worker and app manifest
- 🕓 **Trip history** — "My Rides" view of past bookings, tied to the logged-in session

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| 🎨 Frontend | HTML / CSS / JavaScript (PWA), Leaflet.js, OpenStreetMap tiles |
| ⚙️ Backend | Python, Flask, Flask-CORS |
| 🕸️ Routing engine | NetworkX graph (stops as nodes, transit + walking transfers as edges) |
| 🤖 AI / Recommendation | scikit-learn (route-scoring model) |
| 🔐 Authentication | Firebase Phone Authentication |
| 📊 Data source | Official HMRL Metro GTFS + TGSRTC Bus GTFS (open government data) |
| ☁️ Hosting | Render (backend API) |
| 🗺️ Maps | Leaflet.js + OpenStreetMap (no API key required) |

---


---

## 🚀 Running Locally

**Backend:**
```bash
pip install -r requirements.txt
python app.py
```
The API will start on `http://localhost:5000` 🎉

**Frontend:**
Open `index.html` in a browser (or serve it via any static file server). Update the `API_BASE` constant in `index.html` if pointing to a different backend URL.

---

## 📡 Data Sources

- 🚇 **HMRL Metro GTFS** — [data.opencity.in](https://data.opencity.in) (Telangana Open Data)
- 🚌 **TGSRTC Bus GTFS** — [data.opencity.in](https://data.opencity.in) (Telangana Open Data), 1,031 official routes
- 🚆 **MMTS** — corridor-level data compiled from public timetables

---

## 🗺️ Roadmap

- [ ] 🤝 Official data partnership with TSRTC / HMRL / SCR for live GPS and real-time delays
- [ ] 💳 Real UPI payment gateway integration
- [ ] 🌆 Full-city bus coverage using the complete TGSRTC GTFS feed
- [ ] 📱 Native Android packaging and Play Store launch

---

## 👥 Team
SK JEENATH , N DHARAKESH , P SAHASRA SRI KRITHI
---
## 📄 License
Transit data sourced from official Telangana Open Data GTFS feeds.
