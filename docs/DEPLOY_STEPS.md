# Recruit Lens Deployment Runbook

This guide covers deployment options for Recruit Lens within free-tier infrastructure limits (Hugging Face Spaces, Render, Supabase, Vercel, and Docker Compose).

---

## Architecture & Hosting Free-Tier Fit

| Component | Recommended Free Host | Free-Tier Limits | Footprint in Recruit Lens | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Backend API** | Hugging Face Spaces (Docker) | 2 vCPU, 16 GB RAM, 50 GB disk | Peak RSS ~350 MB, CPU < 0.5s/cand | **Excellent Fit** |
| **Alternative Backend** | Render Web Service | 512 MB RAM, spins down on idle | Peak RSS ~350 MB, 50s cold start | **Viable Fit** |
| **Database** | Supabase (PostgreSQL) | 500 MB DB, 2 direct connections | Schema ~15 MB, asyncpg pooled | **Excellent Fit** |
| **Frontend Portal** | Cloudflare Pages / Vercel | Unlimited bandwidth, CDN edge | Static bundle 701 KB JS / 57 KB CSS | **Instant Edge** |
| **All-in-One Local** | Docker Compose | Local resources | Self-contained, zero cloud cost | **One Command** |

---

## Option 1: One-Click Local Production with Docker Compose

Ensure Docker and Docker Compose are installed:

```bash
# 1. Clone repository
git clone https://github.com/mhd-sajad/Recruit-Lens.git
cd Recruit-Lens

# 2. Start services (PostgreSQL 16 + FastAPI + Static React Frontend)
docker compose up -d --build

# 3. Seed demo accounts and candidate data
docker compose exec app python /app/backend/../scripts/seed_demo_workspace.py

# 4. Open in browser
# http://localhost:8000
# Login: admin@recruitlens.local / Admin123!
```

---

## Option 2: Hugging Face Spaces (Recommended Free Cloud Hosting)

Hugging Face Spaces provides 16 GB RAM on its free CPU tier, easily hosting the full ONNX inference engine and API.

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. Space Name: `recruit-lens`.
3. Space SDK: Choose **Docker** -> **Blank**.
4. Set Repository Secrets in Space Settings:
   - `DATABASE_URL`: `sqlite+aiosqlite:///app/data/recruit_lens.db` (or external Supabase PostgreSQL URL).
   - `SECRET_KEY`: Generate with `openssl rand -hex 32`.
   - `GROQ_API_KEY`: *(Optional)* Your Groq API key for generative LLM text synthesis.
5. Push the repository to the Hugging Face Space git remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/recruit-lens
   git push space main
   ```
6. Hugging Face Spaces builds the multi-stage `Dockerfile`, runs database migrations, and exposes the full application over HTTPS.

---

## Option 3: Supabase (PostgreSQL) + Render (Backend) + Cloudflare Pages (Frontend)

### Step 1: Create Supabase PostgreSQL Database
1. Create a free project at [supabase.com](https://supabase.com).
2. Retrieve the connection string:
   `postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?ssl=require`

### Step 2: Deploy Backend to Render
1. Create a **New Web Service** connected to your GitHub repository.
2. Runtime: **Docker** (using repository `Dockerfile`).
3. Environment Variables:
   - `DATABASE_URL`: Your Supabase connection string.
   - `SECRET_KEY`: Secure 64-char hex string.
   - `ENVIRONMENT`: `production`.
   - `CORS_ORIGINS`: `["https://your-frontend.pages.dev"]`
4. Deploy service. The health check endpoint is `/health`.

### Step 3: Deploy Frontend to Cloudflare Pages
1. In Cloudflare Dashboard, go to **Workers & Pages** -> **Create Application** -> **Pages**.
2. Connect `Recruit-Lens` repository:
   - Framework preset: **Vite**
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
3. Environment variable:
   - `VITE_API_URL`: Your Render backend URL (e.g. `https://recruit-lens-api.onrender.com`).
4. Click **Save and Deploy**.
