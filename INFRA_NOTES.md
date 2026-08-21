# Infra Notes (for reference — no infra changes made here)

## 1. Dead `Dockerfile.frontend` + `docker/nginx.conf` pair

`railway.toml` only builds `Dockerfile.backend`, which itself builds the React app
(`frontend/npm run build`) and copies `frontend/dist` into the backend image. FastAPI
(`backend/main.py`) then mounts that `dist` folder as static files and serves everything —
API and frontend — from a single Railway service on one port.

`Dockerfile.frontend` and `docker/nginx.conf` build a **second**, entirely separate serving
path: an nginx container that serves the built frontend itself and reverse-proxies `/api`
to `BACKEND_URL` (Railway private networking, e.g. `http://backend.railway.internal:8000`).
Nothing in `railway.toml` references `Dockerfile.frontend`, so this path is currently dead
code — it never builds or deploys.

**What it would take to wire up** (only if a two-service split is ever wanted, e.g. to scale
frontend/backend independently or serve the frontend from a CDN-backed edge):
- Add a second service block to `railway.toml` (or a second Railway service in the dashboard)
  pointing `dockerfilePath` at `Dockerfile.frontend`.
- Set `BACKEND_URL` on that new frontend service to the backend service's Railway private
  networking address.
- Point the public domain at the frontend service instead of the backend service.
- Remove the `StaticFiles` mount in `backend/main.py` (or leave it as a fallback) since the
  frontend would no longer be served by FastAPI.
- Decide whether `predict_cache`/`search_cache` (in-process TTLCache) need to move to
  something shared (e.g. Redis) once there are two independently-scaling backend replicas —
  not needed today since there's only one backend instance either way.

Until then, this pair can be deleted or left as reference; it costs nothing sitting unused
in the repo.

## 2. Intermittent DNS / domain issue (decodescents.com, IONOS)

Not investigated as part of this change (out of scope — read-only reference note only).
Things worth checking on the IONOS side if the live domain is intermittently unreachable:
- **DNS record type/target**: confirm the domain's A/CNAME record points at Railway's
  current target (Railway domains can be CNAME'd to a `*.up.railway.app` hostname, or use
  an A record to Railway's edge IPs — if IONOS has a stale A record from before a Railway
  redeploy/domain regeneration, it'll intermittently 404/fail while Railway's edge IP churns).
- **TTL**: a long TTL on the DNS record means DNS changes (including any Railway-side IP
  rotation) take longer to propagate, which can look like intermittent failures right after
  a change.
- **IONOS-side proxying/forwarding**: if IONOS has any "domain forwarding" or parking page
  feature enabled on this domain instead of a plain DNS record, that can intermittently
  intercept the domain instead of `CNAME`ing straight to Railway.
- **Certificate issuance**: Railway auto-provisions a TLS cert once DNS is verified — if DNS
  flaps, cert renewal can fail silently and cause intermittent SSL errors distinct from plain
  unreachability.
- Cross-check in the Railway dashboard under the service's Domains tab — it will flag if the
  custom domain's DNS record doesn't currently match what Railway expects.
