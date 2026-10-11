# Climafeet

Climafeet compares truck routes using checkpoint weather forecasts, load weight, and travel time. It returns up to three TomTom truck routes, samples weather along each route at the selected interval, ranks the routes, and displays a 48-hour corridor heatmap.

## Requirements

- Python 3.12 or newer
- Node.js 22 or newer
- A TomTom API key with Search and Routing access

Open-Meteo supplies forecast data. The map uses MapLibre GL with CARTO basemaps.

## Run locally

In PowerShell, from the repository root:

```powershell
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
# Edit backend/.env and set TOMTOM_API_KEY.
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-dev.txt
```

Start the backend in one terminal:

```powershell
Set-Location backend
.venv\Scripts\python manage.py runserver
```

Start the frontend in another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). Vite proxies `/api` requests to Django at `http://127.0.0.1:8000`.

For a non-local backend, set `VITE_API_BASE_URL` to its origin when building the frontend, for example `https://your-api.azurewebsites.net`. Configure that origin in the backend's `CORS_ALLOWED_ORIGINS` setting. Keep `TOMTOM_API_KEY` on the backend; never add it to a `VITE_` variable.

## Configuration

Copy `backend/.env.example` to `backend/.env` for local development. The server reads these settings:

| Variable | Purpose |
| --- | --- |
| `TOMTOM_API_KEY` | Server-side geocoding and truck routing |
| `DJANGO_SECRET_KEY` | Django secret; use a unique value in production |
| `DJANGO_DEBUG` | Set to `false` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated backend hostnames |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins |
| `CORS_ALLOWED_ORIGIN_REGEXES` | Optional regexes for preview frontend origins |
| `WEATHER_CACHE_SECONDS` | Weather response cache duration (default: 1800 seconds) |

The API accepts a departure up to seven days ahead and a load up to 100,000 lb. Forecast coverage is limited to the provider's available forecast window. Weather thresholds and load adjustments are implemented in `backend/trips/services/risk.py`.

## Deploy

The repository includes GitHub Actions workflows for the backend on Azure App Service and the frontend on Azure Static Web Apps. Create the Azure resources, then add these repository settings:

| Setting | Kind | Used by |
| --- | --- | --- |
| `AZURE_WEBAPP_NAME` | Repository variable | Backend workflow |
| `AZURE_WEBAPP_PUBLISH_PROFILE` | Repository secret | Backend workflow |
| `AZURE_STATIC_WEB_APP_NAME` | Repository variable | Frontend workflow enablement |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Repository secret | Frontend workflow |
| `VITE_API_BASE_URL` | Repository variable | Frontend build, backend origin |

Set the backend App Service startup command to `sh startup.sh` and configure its application settings with the production values above, including the TomTom key and frontend origin. On the frontend workflow, `VITE_API_BASE_URL` must be the backend's HTTPS origin without a trailing slash. The backend workflow deploys on changes under `backend/`; the frontend workflow deploys on changes under `frontend/`. Both can also be started manually from the Actions tab.

## Project layout

- `frontend/` — React, TypeScript, Vite, MapLibre map and heatmap UI
- `backend/` — Django REST API, TomTom routing/geocoding, Open-Meteo forecasts, risk and recommendation logic
- `.github/workflows/` — CI and Azure deployment workflows

The API endpoints are `GET /api/health`, `GET /api/geocode`, `POST /api/trips/plan`, and `POST /api/heatmap`.
