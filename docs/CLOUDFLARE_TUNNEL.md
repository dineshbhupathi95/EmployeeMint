# Exposing EmployeeMint via Cloudflare Tunnel

This guide explains how to run EmployeeMint locally and share it with phones, other laptops, or anyone outside your machine using **Cloudflare Quick Tunnels** (`trycloudflare.com`).

For same-Wi‑Fi access without a tunnel, see [Same Wi‑Fi (LAN) access](#same-wi-fi-lan-access).

---

## Prerequisites

- EmployeeMint running locally (backend + frontend + infra)
- `cloudflared` installed

```bash
brew install cloudflared
```

---

## Architecture overview

EmployeeMint has two local services:

| Service  | Local URL              | Default port |
|----------|------------------------|--------------|
| Frontend | http://localhost:5173  | 5173         |
| Backend  | http://localhost:8000  | 8000         |

You can expose them in two ways:

### Option A — One tunnel (recommended)

Only tunnel the **frontend**. Vite proxies `/api` to the local backend.

```
Phone/Browser → Cloudflare URL → cloudflared → Vite (5173) → /api → Backend (8000)
```

### Option B — Two tunnels

Tunnel frontend and backend separately. Set `VITE_API_BASE_URL` to the backend tunnel URL.

```
Phone/Browser → Frontend tunnel → Vite (5173)
Phone/Browser → Backend tunnel  → FastAPI (8000)  (API calls from browser)
```

---

## Step 1 — Start local services

### Infrastructure

From the project root:

```bash
cp .env.example .env
docker compose up -d postgres redis minio
```

### Backend (terminal 1)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.scripts.seed   # first time only
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Verify locally:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Login: `admin@employeemint.local` / `changeme`

---

## Step 2 — Install and run Cloudflare tunnels

Keep each `cloudflared` process running in its own terminal. **Closing the terminal stops the tunnel and invalidates the URL.**

### Option A — One tunnel (frontend only)

**Terminal 3:**

```bash
cloudflared tunnel --url http://127.0.0.1:5173
```

Copy the URL from the output, for example:

```
https://warrior-she-salaries-beginners.trycloudflare.com
```

Share: `https://YOUR-FRONTEND-TUNNEL.trycloudflare.com/login`

### Option B — Two tunnels (frontend + backend)

**Terminal 3 — frontend:**

```bash
cloudflared tunnel --url http://127.0.0.1:5173
```

**Terminal 4 — backend:**

```bash
cloudflared tunnel --url http://localhost:8000
```

You will get two URLs, for example:

- Frontend: `https://warrior-she-salaries-beginners.trycloudflare.com`
- Backend:  `https://largely-likes-typically-gourmet.trycloudflare.com`

---

## Step 3 — Configure environment variables

Edit the project root `.env` file (not `.env.example`).

**Path:** `/EmployeeMint/.env`

### Option A — One tunnel

```env
# Leave empty so the browser calls /api on the same Cloudflare host (Vite proxies to localhost:8000)
VITE_API_BASE_URL=

# Comma-separated — no semicolons. Add your frontend tunnel URL.
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://YOUR-FRONTEND-TUNNEL.trycloudflare.com
```

### Option B — Two tunnels

```env
VITE_API_BASE_URL=https://YOUR-BACKEND-TUNNEL.trycloudflare.com

CORS_ORIGINS=http://localhost:5173,https://YOUR-FRONTEND-TUNNEL.trycloudflare.com
```

### Restart after changes

| Variable            | Restart required      |
|---------------------|-----------------------|
| `CORS_ORIGINS`      | Backend               |
| `VITE_API_BASE_URL` | Frontend (Vite dev)   |

---

## Step 4 — Vite configuration (already set)

**Path:** `frontend/vite.config.ts`

These settings are required for Cloudflare tunnels:

```ts
server: {
  port: 5173,
  host: true,                        // listen on all interfaces
  allowedHosts: [".trycloudflare.com"], // allow any quick-tunnel hostname
  proxy: {
    "/api": {
      target: "http://localhost:8000", // Option A: proxy API to local backend
      changeOrigin: true,
    },
  },
},
```

- `allowedHosts` uses `.trycloudflare.com` so **any** quick-tunnel URL works without editing this file each time.
- For **Option B** (two tunnels), the proxy is unused if `VITE_API_BASE_URL` points to the backend tunnel.

---

## Files to update when tunnel URLs change

Quick tunnel URLs change every time you restart `cloudflared`. Update these when you get a new URL:

| File | What to change | When |
|------|----------------|------|
| `.env` | `CORS_ORIGINS` — add frontend tunnel URL | Every new frontend tunnel |
| `.env` | `VITE_API_BASE_URL` — backend tunnel URL | Option B only, every new backend tunnel |
| `frontend/vite.config.ts` | Usually **no change** (`allowedHosts` covers all tunnels) | Only if using Option A (keep proxy `target` as `http://localhost:8000`) |

You do **not** need to edit:

- `frontend/src/api/client.ts` — reads `VITE_API_BASE_URL` from `.env`
- `backend/app/core/config.py` — reads `CORS_ORIGINS` from `.env`

---

## Same Wi‑Fi (LAN) access

If the other device is on the **same network**, you can skip Cloudflare entirely.

### Find your machine IP

```bash
ipconfig getifaddr en0    # macOS Wi‑Fi
```

Example IP: `192.168.1.29`

### URLs

- Frontend: `http://192.168.1.29:5173`
- API docs: `http://192.168.1.29:8000/docs`

### `.env` for LAN

```env
VITE_API_BASE_URL=
CORS_ORIGINS=http://localhost:5173,http://192.168.1.29:5173
```

Start frontend with:

```bash
npm run dev -- --host 0.0.0.0
```

Start backend with:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Terminal checklist

Keep all of these running while sharing the app:

| Terminal | Command |
|----------|---------|
| 1 | `docker compose up -d postgres redis minio` |
| 2 | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (in `backend/`) |
| 3 | `npm run dev -- --host 0.0.0.0` (in `frontend/`) |
| 4 | `cloudflared tunnel --url http://127.0.0.1:5173` |
| 5 (optional) | `cloudflared tunnel --url http://localhost:8000` |

---

## Troubleshooting

### `Blocked request. This host ("…trycloudflare.com") is not allowed`

Vite rejected the tunnel hostname. Ensure `frontend/vite.config.ts` includes:

```ts
allowedHosts: [".trycloudflare.com"],
host: true,
```

Restart the frontend dev server.

### URL works on your Mac but not on phone / other laptop

1. **Dead tunnel URL** — Quick tunnel URLs expire when `cloudflared` stops. Check DNS:

   ```bash
   nslookup YOUR-TUNNEL.trycloudflare.com
   ```

   If you see `NXDOMAIN`, the URL is dead. Start `cloudflared` again and use the **new** URL.

2. **Using localhost on your Mac** — `http://localhost:5173` only works on the machine running the app. Other devices must use the Cloudflare URL or LAN IP.

3. **`cloudflared` not running** — The tunnel process must stay open in a terminal.

4. **Wrong port** — If Vite moved to another port (e.g. 5174), tunnel the port Vite actually uses:

   ```bash
   cloudflared tunnel --url http://127.0.0.1:5173
   ```

5. **CORS errors on login** — Add the frontend tunnel URL to `CORS_ORIGINS` in `.env` (comma-separated, not semicolons) and restart the backend.

6. **API calls fail from tunnel** — For Option A, keep `VITE_API_BASE_URL` empty. For Option B, set it to the **backend** tunnel URL and restart Vite.

### HTTP 530 from Cloudflare

Cloudflare cannot reach your local service.

- Confirm Vite/backend are running.
- Use `http://127.0.0.1:5173` (not a stale tunnel URL) as the `cloudflared` target.
- Wait 10–30 seconds after starting `cloudflared` for the tunnel to register.

### Login works locally but API fails through tunnel

- Option A: confirm `VITE_API_BASE_URL` is empty and Vite proxy targets `http://localhost:8000`.
- Option B: confirm `VITE_API_BASE_URL` matches the live backend tunnel URL.
- Confirm `CORS_ORIGINS` includes the frontend tunnel URL.

---

## Important limitations

- **Quick tunnels are for development/demo** — no uptime guarantee; URLs change on every restart.
- **Do not use for production** — use a named Cloudflare Tunnel with a Cloudflare account for production.
- **Never commit live tunnel URLs** — keep them in `.env` only (`.env` is not committed).
- **Security** — anyone with the tunnel URL can access your local dev app. Stop `cloudflared` when you are done sharing.

---

## Quick reference

```bash
# Install
brew install cloudflared

# Frontend tunnel
cloudflared tunnel --url http://127.0.0.1:5173

# Backend tunnel (optional, Option B)
cloudflared tunnel --url http://localhost:8000

# After new frontend URL → update .env:
# CORS_ORIGINS=...,https://NEW-FRONTEND.trycloudflare.com

# After new backend URL (Option B) → update .env:
# VITE_API_BASE_URL=https://NEW-BACKEND.trycloudflare.com

# Restart backend (CORS) and frontend (VITE_*)
```

For production deployment patterns, see [docs/HLD.md](HLD.md).
