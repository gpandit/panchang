 # The Pandit — Production Deployment Guide

A step-by-step guide to take The Pandit live: the backend server, the web app, the
admin console, and the iOS + Android apps. Written so a non-technical owner can
follow it (or hand it to a contractor) and know exactly what to buy, in what order,
and what can run in parallel.

**Target scale:** comfortably sustain **10,000 concurrent users**.

---

## 0. The one-minute summary

| Question | Answer |
|---|---|
| **Do I need Kubernetes?** | **No.** Your code already deploys itself with Docker Compose over SSH (see `.github/workflows/staging-deploy.yml`). Kubernetes would throw that working automation away. Stay on Docker Compose. |
| **New VPS or managed?** | **A VPS running Docker, plus managed database + cache.** One mid-size VPS launches you; you scale by adding a second VPS behind a load balancer. No re-architecture needed. |
| **Which host?** | **DigitalOcean** if you want the easiest experience (recommended). **OVHcloud** or **Hetzner** if you want the lowest price. **Time4VPS** only if budget is the single deciding factor. |
| **Rough monthly cost** | **~$45/mo** to launch on one VPS; **~$180–220/mo** for the resilient 10k-user setup. |
| **Biggest non-technical blocker** | The **Swiss Ephemeris commercial licence** *must* be purchased before you put the app in front of the public or in any app store. This is a hard legal gate, not optional. See §2. |

---

## 1. What you are actually deploying

Your project is a "monorepo" — one codebase containing several pieces that work
together. Here is every piece in plain language:

| Piece | What it is | Where it runs |
|---|---|---|
| **Panchang service** | The astronomy engine that calculates the Panchang. The heart of the product. | On your server (Docker) |
| **API gateway** | The traffic controller. Apps and the website talk to this; it talks to the engine and database. | On your server (Docker) |
| **Worker** | Background helper — generates PDFs, sends reminders, warms the cache. | On your server (Docker) |
| **Web app** | The public website (Next.js). | On your server (Docker) |
| **Admin console** | Your private back-office dashboard. | On your server (Docker) |
| **Database (PostgreSQL)** | Stores users, bookings, content. | Managed service (recommended) |
| **Cache (Redis)** | Remembers recent answers so the engine isn't re-run for every visitor. **This is what makes 10k users affordable.** | Managed service or on server |
| **Object storage (S3)** | Stores generated files like PDF calendars. | DigitalOcean Spaces / AWS S3 |
| **Monitoring (Grafana + Prometheus)** | Dashboards and alerts so you know if anything breaks. | On your server (Docker) |
| **Nginx** | The front door — handles HTTPS and routes visitors to the right piece. | On your server (Docker) |
| **iOS app** | Native iPhone/iPad app (Swift). | Apple App Store |
| **Android app** | Native Android app (Kotlin). | Google Play Store |

**Good news:** every server-side piece is already containerised and wired together
in one file — `infra/docker-compose.staging.yml`. You don't assemble anything by
hand; you run one command and Docker starts all of them.

---

## 2. Before you spend a rupee on servers — three hard prerequisites

These have **lead time** (days to weeks) and block launch. Start them on **day one**,
in parallel with everything else.

### 2.1 Swiss Ephemeris commercial licence  ⚠️ HARD LEGAL GATE
The Panchang engine uses Swiss Ephemeris. The free version (AGPL) is **only legal for
private development and testing**. The moment you serve the public, charge money, or
submit to an app store, you legally need the **commercial licence**.

- Your own code enforces this: `tools/check_launch_readiness.py` and the
  `launch-readiness.yml` CI check will **fail any production build** until the licence
  is set to `commercial`.
- **Action:** email Astrodienst AG via
  <https://www.astro.com/swisseph/swephinfo_e.htm#licencing> now. Treat it like any
  other supplier purchase. See `docs/licensing/swiss-ephemeris.md`.

### 2.2 Apple Developer + Google Play accounts
You cannot publish mobile apps without these, and approval/verification can take days.

- **Apple Developer Program** — US $99/year. Sign up at <https://developer.apple.com/programs/>.
  Individual is fine to start; a "Company" account needs a D-U-N-S number (extra lead time).
- **Google Play Developer** — US $25 one-time. Sign up at <https://play.google.com/console/signup>.
  Google now requires identity verification — start early.

### 2.3 A domain name
Buy your domain (e.g. `thepandit.app`) from any registrar (Namecheap, Cloudflare,
GoDaddy). The configs already assume names like `api.thepandit.app` and
`staging.thepandit.app`. ~$15–40/year.

---

## 3. What infrastructure to buy

### 3.1 The recommendation, plainly

**Launch on one VPS. Scale to a small cluster only when traffic proves you need it.**

Because your Panchang and calendar data is the same for everyone in a given
location/date, it is **heavily cached** (nginx caches responses, Redis caches
computations — see `infra/nginx/staging.conf`). That means 10,000 people viewing
"today's Panchang" mostly hit the cache, not the engine. This is why you do **not**
need a big expensive cluster on day one.

### 3.2 Shopping list — Option A: "Launch" (simplest, cheapest)

Everything on one VPS. Perfect for going live and for your first few thousand users.

| Item | Spec | Provider example | ~Cost/mo |
|---|---|---|---|
| 1× VPS (app + DB + cache + monitoring) | 4 vCPU, 8 GB RAM, 80 GB SSD | DigitalOcean "Premium Droplet", OVH VPS Comfort, Hetzner CPX31 | $24–48 |
| Object storage (S3) | 250 GB | DigitalOcean Spaces / Backblaze B2 | $5 |
| Backups (snapshots) | weekly | provider add-on | $5 |
| **Total** | | | **~$35–60/mo** |

> Hetzner (CPX31, ~€15/mo) is the best price/performance if you're comfortable in the EU.
> DigitalOcean costs a bit more but is the friendliest dashboard for a non-technical owner.

### 3.3 Shopping list — Option B: "10k concurrent, resilient" (recommended target)

Splits the database and cache onto managed services (so a server reboot never loses
data and you sleep at night), and runs the app on two servers behind a load balancer
(so one can die without downtime). **This is the setup that comfortably holds 10,000
concurrent users.**

| Item | Spec | Provider (DigitalOcean) | ~Cost/mo |
|---|---|---|---|
| 2× App VPS (Docker) | 4 vCPU, 8 GB each | Premium Droplet ×2 | $96 |
| Managed PostgreSQL | 2 vCPU, 4 GB, 1 standby | Managed Database | $60 |
| Managed Redis/Valkey | 1 GB | Managed Caching | $15 |
| Load Balancer | — | DO Load Balancer | $12 |
| Object storage (S3) | 250 GB | DO Spaces | $5 |
| Monitoring VPS (optional, or co-locate) | 2 vCPU, 4 GB | Droplet | $24 |
| Backups | automatic | included with managed DB | — |
| **Total** | | | **~$190–210/mo** |

**Equivalent on OVHcloud / Time4VPS:** the same shapes exist and are typically 20–40%
cheaper for raw compute, but their managed-database offerings are thinner — on those
providers you'd more likely run PostgreSQL and Redis in Docker on a dedicated VPS
yourself (cheaper, slightly more maintenance). For a non-technical owner, DigitalOcean's
managed DB is worth the premium.

### 3.4 Why NOT Kubernetes (for now)
- Your deployment pipeline (`staging-deploy.yml`) already does SSH → `docker compose pull`
  → `docker compose up`. It works today. Kubernetes would mean rewriting all of it.
- Kubernetes adds a control plane to babysit, a steeper learning curve, and usually
  **higher** cost at this scale.
- Docker Compose on a VPS comfortably serves 10k concurrent cached users. Revisit
  Kubernetes only when you're running many servers across regions — a good problem to
  have later, not a launch decision.

---

## 4. The order of operations (what's first, what's parallel)

Think of it as **three lanes running at the same time.** The only strict rule:
**the backend server must be live before the mobile apps can be submitted**, because
the apps need a real API to talk to and reviewers will test them.

```
WEEK 1                      WEEK 2                       WEEK 3
─────────────────────────────────────────────────────────────────────
LANE 1  ┌─ Buy Swiss Ephemeris licence ────────► (arrives) ──► set in prod secrets
PAPER-  ├─ Apple Developer signup ──► verified
WORK    ├─ Google Play signup ──────► verified
(do     └─ Buy domain
first)

LANE 2          ┌─ Provision VPS ─► Install Docker ─► Deploy backend+web+admin ─► Verify
SERVER          └─ Point DNS ──────────────────────► HTTPS certificates

LANE 3                              ┌─ Build iOS → TestFlight ──► App Store review
MOBILE                              └─ Build Android → Play internal ──► Play review
(needs LANE 2 live first)
```

**Recommended sequence:**
1. **Day 1 (parallel):** Start all of Lane 1 (licence + accounts + domain). These have
   waiting time you can't shortcut.
2. **Day 1–3:** Do Lane 2 (stand up the server). See §5.
3. **After the server is live and verified:** Do Lane 3 (mobile). iOS and Android can be
   built **in parallel** by two people, or one after the other. See §6.
4. **Final gate:** Once the Swiss Ephemeris commercial licence has arrived, flip the
   production build to `commercial` (§5.7) and submit the apps for public release.

---

## 5. LANE 2 — Stand up the server (step by step)

> You'll use the server provider's website for the first part, then a "terminal"
> (a black text window where you type commands) for the rest. Copy-paste the commands
> exactly. Lines starting with `#` are explanations — don't type those.

### 5.1 Create the VPS
1. Sign up at DigitalOcean (or OVH / Hetzner).
2. Create a new server ("Droplet" on DigitalOcean):
   - **Image / OS:** Ubuntu 24.04 LTS
   - **Size:** 4 vCPU / 8 GB RAM (Option A) — start here, resizing later is one click.
   - **Authentication:** choose **SSH key** (more secure than password). The site will
     walk you through creating one; save the file it gives you.
   - **Hostname:** `pandit-prod-1`
3. When it finishes, note the server's **public IP address** (e.g. `203.0.113.10`).

### 5.2 Point your domain at the server
In your domain registrar's DNS settings, create these records (replace the IP):

| Type | Name | Value |
|---|---|---|
| A | `@` (or `thepandit.app`) | `203.0.113.10` |
| A | `api` | `203.0.113.10` |
| A | `admin` | `203.0.113.10` |
| A | `grafana` | `203.0.113.10` |

DNS can take up to an hour to spread. Move on while it does.

### 5.3 Log into the server
On your Mac, open the **Terminal** app and type (use your real IP):
```bash
ssh root@203.0.113.10
```
Type `yes` if it asks to trust the server. You're now "inside" the server.

### 5.4 Install Docker (one block, copy-paste)
```bash
# Update the server and install Docker + Compose
apt update && apt -y upgrade
curl -fsSL https://get.docker.com | sh
docker --version   # should print a version number
```

### 5.5 Get the code and configuration onto the server
```bash
# Create the folder the deploy pipeline expects
mkdir -p /opt/pandit-prod && cd /opt/pandit-prod

# Get the code (use your repo URL; you may need a deploy token for a private repo)
git clone https://github.com/gpandit/pandit-xyz.git .

# Create your secrets file from the template
cp infra/env.staging.example .env.prod
```

### 5.6 Fill in your secrets
Open the secrets file with a simple editor:
```bash
nano .env.prod
```
Replace every `CHANGE_ME` with a real value. To generate strong random passwords, run
this in another terminal tab and paste the output:
```bash
openssl rand -hex 32   # run once per CHANGE_ME password
```
Key fields:
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `API_SECRET_KEY`, `GRAFANA_ADMIN_PASSWORD` — random strings.
- `S3_*` — from your DigitalOcean Spaces / S3 bucket (create one in the provider dashboard, "API → Spaces keys").
- `IMAGE_REGISTRY=ghcr.io/gpandit` — leave as is.

Save in nano with **Ctrl+O, Enter**, then exit with **Ctrl+X**.

### 5.7 ⚠️ Production licence + build profile
When your Swiss Ephemeris commercial licence has arrived, edit `.env.prod`:
```
PANCHANG_BUILD_PROFILE=production
PANCHANG_EPHEMERIS_LICENSE=commercial
```
Until the licence arrives, **leave these as `staging` / `agpl`** and keep the site
private (don't advertise it). This keeps you legal.

> The compose stack reads `PANCHANG_BUILD_PROFILE` and `PANCHANG_EPHEMERIS_LICENSE` from
> your `.env.prod` (defaulting to the safe `staging` / `agpl` build if unset), so editing
> the env file is all that's needed — you don't touch the compose file.

### 5.8 HTTPS certificates (the padlock)
nginx listens on `:443` and **will not start** until two certificate files exist:
`infra/nginx/certs/staging.crt` and `infra/nginx/certs/staging.key`. You must create
them **before** the next step, even when Cloudflare is in front (Cloudflare still needs a
certificate on your server — its "Full" mode talks HTTPS to the origin).

**Recommended (Cloudflare + a free Cloudflare Origin Certificate):**
1. Point your domain's nameservers to **Cloudflare** and set SSL mode to **Full**.
2. In Cloudflare → **SSL/TLS → Origin Server → Create Certificate**. Copy the
   certificate and private key it shows you.
3. On the server, save them with the exact names nginx expects:
   ```bash
   cd /opt/pandit-prod
   nano infra/nginx/certs/staging.crt   # paste the certificate, save (Ctrl+O, Enter, Ctrl+X)
   nano infra/nginx/certs/staging.key   # paste the private key, save
   ```

**Quick alternative (self-signed, to get the stack up now)** — fine behind Cloudflare
"Full"; replace with a real cert before launch:
```bash
cd /opt/pandit-prod
openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
  -keyout infra/nginx/certs/staging.key \
  -out infra/nginx/certs/staging.crt \
  -subj "/CN=thepandit.app"
```
*(Production-grade alternative for the technically inclined: run Certbot/Let's Encrypt and
have it write into `infra/nginx/certs/` — ask a contractor to wire it in.)*

### 5.9 Start everything

You have two ways to get the app images. **Option A** pulls images that CI already
built; **Option B** builds them on the server (use this for a first deploy, or if CI
hasn't published images yet).

**Important — image tag:** CI publishes each image as the commit SHA and as
`staging-latest`. It does **not** publish a `latest` tag. So `.env.prod` ships with
`IMAGE_TAG=staging-latest`; leave it as that (or pin a specific commit SHA). If you set
`IMAGE_TAG=latest`, the pull will fail with `not found`.

**Option A — pull pre-built images (when CI has published them):**
```bash
cd /opt/pandit-prod
# Create a GitHub token with the read:packages scope first (see note below), then:
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u gpandit --password-stdin

docker compose --env-file .env.prod -f infra/docker-compose.staging.yml pull
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml up -d
```
> The GitHub token must be a real **Personal Access Token** with the **`read:packages`**
> scope (GitHub → Settings → Developer settings → Tokens). Without it you'll get `denied`.

**Option B — build images on the server (first deploy / no published images):**
```bash
cd /opt/pandit-prod
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml build
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml up -d
```
> The Panchang image compiles `pyswisseph`, and the web image (Next.js) is memory-hungry.
> If a build is `Killed` for out-of-memory on an 8 GB server, add swap once and re-run
> `build`: `fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`

> Note: the file is named `...staging.yml` but it *is* your full production stack. When
> you're ready, copy it to `docker-compose.production.yml` and swap the staging domain
> names for production ones — but it works as-is to get live.

### 5.10 Set up the database tables
```bash
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml \
  run --rm api python -m alembic upgrade head
```
This runs the Alembic migrations against Postgres. A successful run ends with a line
like:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_temple, initial temple schema + demo seed
```
It creates the `temples` and `temple_admin_accounts` tables and seeds one demo temple
(`temple-siddhivinayak`) plus its admin login, so the Temple Display has data
immediately. The migration is idempotent — re-running it is a safe no-op once the
schema is at `head`.

> If you instead see `No module named alembic`, you're running an **old API image**
> that predates the database layer. Rebuild/pull the API image (§5.9) and retry.

### 5.11 Verify it's working
```bash
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml ps
# Every row should say "healthy" or "running"

curl -k https://api.thepandit.app/healthz   # should return OK / 200
```
Then open in your browser:
- `https://thepandit.app` — the website
- `https://api.thepandit.app/docs` — the API documentation page
- `https://admin.thepandit.app` — the admin console
- `https://grafana.thepandit.app` — your dashboards (log in with the Grafana password you set)

### 5.12 Turn on automatic deploys (optional but recommended)
Your repo already has the automation (`.github/workflows/staging-deploy.yml`). To use it,
add these in GitHub → your repo → **Settings → Secrets and variables → Actions**:
`STAGING_HOST` (your IP), `STAGING_SSH_USER` (`root`), `STAGING_SSH_KEY` (your private
key), plus the `STAGING_*` password secrets. After that, **every change you merge
deploys itself** — no more manual steps.

---

## 6. LANE 3 — Publish the mobile apps

> Do this **after** the server is live (§5), because Apple/Google reviewers will open
> the app and it must reach a working API. Your repo already has the build automation
> in `.github/workflows/mobile-staging.yml` (iOS → TestFlight, Android → Play internal).

iOS and Android are independent — **build them in parallel** if you have help.

### 6.1 iOS (requires a Mac)
1. Confirm the Apple Developer account (§2.2) is active.
2. In **App Store Connect** (<https://appstoreconnect.apple.com>), create a new app
   record: name "The Pandit", bundle ID matching `apps/ios/project.yml`.
3. The CI workflow builds and uploads to **TestFlight** automatically on each release.
   To do it by hand on your Mac:
   ```bash
   cd apps/ios
   brew install xcodegen
   xcodegen generate          # creates the Xcode project
   open ThePandit.xcodeproj   # opens Xcode
   ```
   In Xcode: set the API URL to `https://api.thepandit.app/v1`, choose **Product →
   Archive**, then **Distribute → TestFlight**.
4. Test via TestFlight on your own iPhone. When happy, submit for **App Store review**
   in App Store Connect. Review typically takes 1–3 days.

### 6.2 Android
1. Confirm the Google Play account (§2.2) is active.
2. In **Play Console** (<https://play.google.com/console>), create the app "The Pandit".
3. The CI workflow builds and uploads to the **internal testing** track. To do it by
   hand:
   ```bash
   cd apps/android
   ./gradlew bundleRelease    # produces an .aab file to upload
   ```
   You'll need an "upload key" (signing key) — Play Console guides you through "Play App
   Signing" the first time.
4. Upload the `.aab` to the internal track, test on your phone, then **promote to
   Production**. First-time Google review can take a few days.

### 6.3 Final public-launch checklist
- [ ] Swiss Ephemeris commercial licence received and set to `commercial` in prod (§5.7)
- [ ] `PANCHANG_BUILD_PROFILE=production` and `launch-readiness` CI check is green
- [ ] HTTPS working on all domains
- [ ] Privacy policy + support URL ready (both stores require them)
- [ ] App Store + Play store listings (screenshots, description) complete

---

## 7. Reaching 10,000 concurrent users

You don't need this on day one. Here's how to grow into it, simplest lever first:

1. **Cache first (free).** Confirm nginx and Redis caching are doing their job — in
   Grafana, watch the `X-Cache-Status` hit rate. High cache hits = most traffic never
   touches the engine. This alone gets you most of the way.
2. **Resize the VPS (one click).** If CPU is high, bump the single server to 8 vCPU /
   16 GB. Vertical scaling is the easiest win.
3. **Move to Option B (§3.3).** Split out managed PostgreSQL + Redis, add a second app
   VPS, put both behind a load balancer. The `api`, `web`, and `worker` containers are
   stateless, so running two copies "just works."
4. **Load-test to prove it.** Your repo already ships a festival-spike load test
   (`tests/load/festival_spike.py`) with SLO targets (p95 < 300 ms for
   `/v1/panchang/today`). Run it against production-like infra before a big festival:
   ```bash
   locust -f tests/load/festival_spike.py --headless \
     --users 2000 --spawn-rate 50 --run-time 5m \
     --host https://api.thepandit.app
   ```
   If it passes the SLOs in `tests/load/assert_slos.py`, you're ready.
5. **Add a CDN (Cloudflare).** Put Cloudflare in front of the website and cacheable API
   paths. It absorbs festival spikes at the edge, often for free, and is the cheapest
   way to handle sudden 10k+ surges.

**Bottom line:** Option B + Cloudflare in front comfortably sustains 10,000 concurrent
users for this workload, because the data is highly cacheable.

---

## 8. Ongoing running costs & housekeeping

| Item | Cost |
|---|---|
| Servers + DB + cache (Option B) | ~$190–210/mo |
| Object storage | ~$5/mo |
| Domain | ~$2/mo (annual) |
| Apple Developer | $99/year |
| Google Play | $25 once |
| Swiss Ephemeris commercial licence | one-time/annual — per Astrodienst quote |
| Cloudflare | free tier is enough to start |

**Routine housekeeping (or hand to a contractor):**
- Backups: enable provider snapshots + managed-DB automatic backups. Test a restore once.
- Updates: `apt upgrade` on the VPS monthly; let CI redeploy app images.
- Monitoring: make sure Alertmanager points at your Slack/email (`SLACK_WEBHOOK_URL`).
- Security: keep the SSH key private; never commit `.env.prod` or the licence key.

---

## Appendix — quick reference of the most-used commands

```bash
# Log into the server
ssh root@YOUR_SERVER_IP

# See what's running
cd /opt/pandit-prod
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml ps

# View logs for one service (e.g. the API)
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml logs -f api

# Restart everything after a change
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml up -d

# Pull the latest images and restart
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml pull
docker compose --env-file .env.prod -f infra/docker-compose.staging.yml up -d
```
