# UpWise — Backend API

Backend for **UpWise**, a growth & loyalty platform for small offline businesses in Kazakhstan
(coffee shops, clothing stores, beauty salons, service points) competing with Kaspi/Wildberries/Ozon
for customer attention. Built for the SERPIN Business Tournament case.

Matches the frontend flow: `Landing → Login → Dashboard → AI Assistant → Campaigns → Customers →
Analytics → Settings → Admin Panel` — one app, one Sidebar/Header, single source of truth via this API.

## Stack

- **FastAPI** + **SQLAlchemy 2.0** — REST API, ORM
- **SQLite** by default (zero setup) — swap to Postgres/Supabase via `DATABASE_URL` env var, no code changes
- **JWT** auth (python-jose + passlib/bcrypt)
- **Anthropic API** for AI copy generation and tool recommendations, with a deterministic
  rule-based fallback (`app/ai.py`) when no API key is set — the demo never breaks on stage
- **qrcode** for campaign QR codes (scan-at-checkout, no real POS integration needed for the MVP)

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # optional — sane defaults work out of the box
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for interactive Swagger UI (all endpoints, try-it-out included).

On first run the DB is created and seeded automatically with:
- 5 categories, 10 catalog tools, 6 admin-managed campaign templates, 5 business types
- **Admin account**: `admin@upwise.kz` / `admin123`
- **Demo business account**: `demo@upwise.kz` / `demo1234` (a coffee shop with 12 mock customers
  and 2 campaigns already running, so Dashboard/Analytics/CRM aren't empty on first login)

## API overview

| Area | Routes | Notes |
|---|---|---|
| Auth & onboarding | `POST /auth/register`, `/auth/login`, `GET /auth/me`, `PATCH /auth/business` | Registration captures business type/size/goal and immediately triggers AI recommendations |
| Reference data | `GET /meta/categories`, `/meta/business-types` | For onboarding & catalog filter dropdowns |
| Tools catalog | `GET /tools`, `POST /tools/{id}/favorite`, `POST /tools/{id}/activate` | Filter by `category`, `tool_type`, `favorites_only`, `activated_only` |
| Campaigns | `POST /campaigns`, `GET /campaigns`, `PATCH /campaigns/{id}/status`, `GET /campaigns/{id}/qr.png`, `POST /campaigns/{id}/simulate-redemption` | AI generates title/text/predicted ROI; QR code per campaign |
| Customers (CRM) | `GET/POST /customers`, `GET /customers/segments/summary` | Value/churn scoring is deterministic (`app/scoring.py`), auto-computed on create |
| Analytics | `GET /analytics/overview` | Revenue, new/repeat customers, channel performance, revenue trend |
| Dashboard | `GET /dashboard` | Aggregated view: active tools/campaigns, top recommendations, recent activity |
| Recommendations | `GET /recommendations`, `POST /recommendations/generate`, `.../apply`, `.../dismiss` | The "система рекомендаций" — AI or rules, matched to business profile |
| Admin panel | `/admin/tools`, `/admin/categories`, `/admin/campaign-templates`, `/admin/business-types` (full CRUD), `GET /admin/stats`, `GET /admin/users` | Requires `is_admin`; all mutations logged to `admin_logs` |

All routes except `/auth/register`, `/auth/login`, `/meta/*`, and `/health` require
`Authorization: Bearer <token>`.

## How this maps to the case's mandatory modules

- **Главная страница / Каталог инструментов** → `/meta/*`, `/tools` (categories, filters, favorites)
- **Бизнес-инструменты** (создание акций, CRM, аналитика) → `/campaigns`, `/customers`, `/analytics`
- **Личный кабинет бизнеса** → `/dashboard` (active tools, stats, history, recommendations)
- **Система рекомендаций** → business profile captured at registration + `/recommendations`,
  powered by `app/ai.py` (Claude when available, rule-based fallback otherwise — same worked
  examples as the case brief: "2+1" for coffee shops, repeat-visit discounts + CRM for salons)
- **Админ-панель** → `/admin/*` full CRUD over tools/categories/templates/business types + platform stats

## AI usage & mock data

Two AI-backed features, both gracefully degrading to rules if `ANTHROPIC_API_KEY` is unset:
1. `recommend_tools_for_business()` — onboarding & AI Assistant recommendations
2. `generate_campaign_copy()` — campaign title/text/predicted ROI generation

Customer value/churn scoring (`app/scoring.py`) is intentionally rule-based (recency + frequency +
monetary heuristic), not an LLM call — it needs to be instant, explainable, and free to run on every
list request. Seed data (`app/seed_data.py`) provides realistic mock customers/campaigns so every
screen has content immediately after a demo login.

## Scaling path (for the pitch deck)

- Swap SQLite → Postgres/Supabase (`DATABASE_URL`) — no application code changes needed
- Real QR redemption at checkout via a lightweight POS webhook (iiko/r_keeper) instead of manual
  `simulate-redemption`
- Kaspi Pay API integration for in-app payment/redemption
- Move campaign delivery (`channel: sms/email/social`) from mock counters to real Telegram
  Bot API / SMS gateway sends
