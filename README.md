# 🏃‍♂️ reActive

A self hosted fitness tracking and visualization app that reads **FIT, TCX (and future GPX)** files and displays them for analysis and visualization.

I began working on this app years ago as I was unhappy with the original desktop Garmin app that came with my Forerunner 305 (ie. there was no Linux version available). Over the years I tried a few desktop alternatives, and about 2015 I built my own using php for the api and javasctipt and Backbone for the browser-based user interface. I evenually migrated the backend to a python/Flask architecture. Recently, I had some changes I wanted to make and decided to move away from Backbone, settling on Vue 3.

The app was originally meant to move away from storing personal fitness data on Garmin's cloud service. It can still do so, but I have recently implemented reading of data from the Garmin api as well.

This Readme file is a work in progress. Much of it is just an AI generated summary, but I will eventually get it in shape. The application however is fully functioning but relies on an existing MariaDB database I have been using for years. There is a second docker compose file that should generate a blank database with all the required tables, but I have yet to test that out.

---

## 🚀 Features

## 🎥 Screenshots & Demo


### 🗺️ Route Map with Metric Colouring

Visualize activities with dynamic colouring based on grade, heart rate, speed, or power.

![Route Map Demo](./docs/gifs/route-map.gif)

### Climb Analysis

The application has climb analysis functions for sports that involve significant elevation gain. Climbs are identified automatically and the start and extent of the climb marked on the route map for the activity. A climb profile graph is also shown for activities with climbs. This card shows the climb profile, colour coded by grade percentage, along with the cycling climb category, average grade, and maximum grade. The user can scroll through the climbs and the map will synchronize to show the geographic extent of each climb as it is viewed in the climb profile card.

---

## Equipment Usage and Maintenance Management

This page allows you to manage your sports equipment. For consumable items like shoes you can set a life span and the app will track usage and let you know when the life of the item is up. This is very important for items like running shoes in order to prevent injury. For items like bikes, a maintenance tracker function is available so you can keep track of what has been done on the item and when. The life of the item can be set based on the service life of a key component. For instance on a bicycle you could track the service life of your tires or chain to know when to inspect them for possible replacement.

### ❤️ Heart Rate Zones

Time-in-zone visualization with automatically computed or device-provided zones.

![HR Zones](./docs/images/hr-zones.png)

---

### ⚡ Power Zones

Coggan-based power zones with fallback computation from activity records.

![Power Zones](./docs/images/power-zones.png)

---

### 📊 Interactive Hover Sync

Hover over charts or map to highlight corresponding points across all views.

![Hover Sync](./docs/gifs/hover-sync.gif)

---

### 🧭 Multi-Activity Support

Overlay multiple activities and compare metrics visually.

![Multi Activity](./docs/images/multi-activity.png)


### 📥 Multi-Format Parsing

* ✅ FIT (Garmin / device-native)
* ✅ TCX (Training Center XML)
* 🔜 GPX support (planned)

---

### 🔄 Unified Data Pipeline

All input formats are normalized into a single schema:

```json
{
  "sessions": [],
  "laps": [],
  "records": [],
  "zones": {
    "heart_rate": {},
    "power": {}
  }
}
```

This ensures:

* Consistent frontend behavior
* Format-agnostic analytics
* Easier extensibility

---

### 🧠 Smart Zone Computation

Supports:

* ✅ Device-provided zones (FIT)
* ✅ Precomputed zones (TCX)
* ✅ Fallback computation from records

#### Heart Rate Zones

* Based on % of max HR
* Automatically inferred if not present

#### Power Zones

* Based on % of FTP (Coggan model)
* Fully computed when missing

---

### 🗺️ Interactive Map (Vue + Leaflet)

* Route visualization with:

  * Gradient coloring by:

    * Grade
    * Heart rate
    * Speed
    * Power
* Hover sync across components
* Downsampling for performance
* Multi-activity support

---

### 📊 Data Visualizations

* Time in zone charts (HR + Power)
* Metric cards (HR, speed, etc.)
* Clean reusable components

---

## 🏗️ Project Structure

```bash
backend/
│
├── app/
│   ├── parsers/        # FIT, TCX parsing logic
│   ├── models/         # Typed data models (Record, Lap, Session, etc.)
│   ├── utils/          # Time, validation, helpers
│   ├── services/       # Zone computation, normalization
│   └── hrm4.py         # Main API route
│
├── wsgi.py

frontend/
│
├── components/
│   ├── RouteMap.vue
│   ├── HRZoneCard.vue
│   └── MetricCard.vue
│
├── composables/
├── views/
└── main.js
```

---

## 🔧 Backend Architecture

### Data Flow

```
FIT / TCX File
      ↓
Parser (format-specific)
      ↓
Normalized Models (Record, Lap, Session)
      ↓
Zone Computation (HR + Power)
      ↓
Unified JSON API
```

---

### Core Models

* `Record` → individual trackpoint
* `Lap` → grouped records
* `Session` → full activity
* `Zones` → HR / Power distributions

---

### Key Concepts

#### ✔ Typed Data Models

* Replaces raw dict iteration
* Centralizes validation
* Improves maintainability

#### ✔ Validation Layer

* Field-level validation
* Handles NaN, missing values, type coercion

#### ✔ Graceful Fallbacks

* Missing data is computed where possible
* Prevents frontend breakage

---

## 🎨 Frontend Architecture

### Vue 3 + Composition API

* Reactive data handling
* Modular components
* Clean separation of concerns

---

### RouteMap Component

Handles:

* Track normalization
* Multi-lap merging
* Metric-based coloring
* Hover interaction

---

### Zone Components

* Unified schema supports:

  * HR zones
  * Power zones
* Easily extendable to other metrics

---

## ⚡ Performance Optimizations

* Track downsampling for map rendering
* Lazy map initialization
* Deferred polyline rendering
* Minimal reactivity overhead

---

## 🧪 Example API Response

```json
{
  "sessions": [...],
  "laps": [...],
  "records": [...],
  "zones": {
    "heart_rate": {
      "type": "heart_rate",
      "source": "computed",
      "zones": [...]
    },
    "power": {
      "type": "power",
      "source": "computed",
      "zones": [...]
    }
  }
}
```

---

## 🛠️ Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
```

---

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## ⚠️ Known Challenges

* FIT files vary widely by device/vendor
* TCX lacks many advanced metrics
* Timezone normalization can be tricky
* Large files require careful performance handling

---

## 🔮 Future Improvements

* GPX parser
* Cadence & advanced metrics
* Training load / TSS
* Segment detection
* Caching layer for large files
* Web worker offloading for parsing

---

## 🤝 Contributing

Contributions welcome! Suggested areas:

* Additional file format support
* Visualization improvements
* Performance tuning
* Test coverage

---

## 📄 License

MIT License

---

## 🙌 Acknowledgements

* Garmin FIT SDK concepts
* Leaflet for mapping
* Chart.js for visualizations

---

## 💡 Philosophy

> Normalize everything early, and the rest of the system becomes simple.

This project is built around the idea that **data consistency beats format-specific complexity**.

---

## 🐳 Deployment (Docker)

This repository supports two deployment models:

- Use an external MariaDB server (e.g. your own managed DB) and run the services with `docker-compose`.
- Run a MariaDB container locally (optional) and let compose initialize the database using an SQL script.

Files of interest:

- `docker-compose.yml` — primary compose file for backend + frontend (reads variables from `.env`).
- `docker-compose.db.yml` — optional compose file that adds a MariaDB service and named volume.
- `backend/scripts/init_db.sql` — initialization SQL executed when MariaDB container initializes.
- `.env.example` — example environment variables. Copy to `.env` and customize (do NOT commit secrets).

Quick start (external DB)

1. Create a `.env` at the repo root from `.env.example` and fill values. Set `DB_HOST` to your DB server hostname.
2. Build and start the services:

```bash
cp .env.example .env
# edit .env and set DB_* and VITE_API_BASE_URL appropriately
docker-compose up --build -d
```

Notes:
- The backend reads DB connection info from environment variables (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).
- The frontend's `VITE_API_BASE_URL` must be set at build time; `docker-compose` passes it as a build arg so the produced static site points to your backend.

Quick start (include MariaDB in compose)

If you want the repo to create and run a MariaDB service for you, use the extra compose file:

```bash
cp .env.example .env
# set DB_USER/DB_PASSWORD/MYSQL_ROOT_PASSWORD in .env
docker-compose -f docker-compose.yml -f docker-compose.db.yml up --build -d
```

The MariaDB image will execute `backend/scripts/init_db.sql` on first initialization to create the database/schema. Adjust that SQL file as needed to match your production schema.

How this supports both cases

- `docker-compose.yml` is written to read DB host/credentials from `.env`. For an external DB, set `DB_HOST` to that host.
- For a local DB, start the additional compose file; set `DB_HOST` to `db` (the service hostname) in `.env` or rely on the `MYSQL_DATABASE` and `MYSQL_USER` environment variables provided by the `db` service.

Security & production notes

- Do not commit `.env` with real credentials.
- For production, prefer Docker secrets (Swarm) or your orchestrator's secret store.
- Use a reverse proxy with TLS (nginx/Traefik) in front of the services for HTTPS.
- Use named volumes for persistent storage and backups for DB and uploads.

If you want, I can make a small GitHub Actions workflow to build and push images to a registry and a sample deployment script to pull and restart on your server.

---
