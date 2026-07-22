# ValenciaGuard

Property management web app for a small real estate company in Valencia, Spain.
The company manages rental properties for Chinese owners living abroad; the app
protects owner interests under Spanish rental law (LAU — Ley de Arrendamientos Urbanos).

## Stack

- **Backend**: FastAPI + SQLModel/SQLAlchemy, SQLite by default (PostgreSQL-ready via `DATABASE_URL`)
- **Frontend**: Jinja2 templates + HTMX (CDN), no build step
- **Auth**: Starlette `SessionMiddleware`, signed session cookie, CSRF token per session
- **AI**: Kimi API (OpenAI-compatible) with automatic mock fallback when no key is set
- **Reports**: fpdf2 PDF monthly reports in Chinese

## Local setup

```bash
python -m venv .venv          # Python 3.12+
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then edit .env (at least SECRET_KEY)
.venv/bin/python -m scripts.seed
.venv/bin/uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/login

### Seed credentials

| User    | Password   | Role  | Lands on                    |
|---------|------------|-------|-----------------------------|
| `admin` | `admin123` | admin | `/dashboard` (Spanish UI)   |
| `owner1`| `owner123` | owner | `/owner-portal` (中文 UI)   |

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

Covers: LAU date calculations, IRAV rent-increase math, auth & owner-portal
scoping, CSRF enforcement, upload validation (extension + magic-byte sniffing).

## Alert checks (cron)

Alert generation runs automatically on admin dashboard load, and standalone via:

```bash
.venv/bin/python -m app.services.alerts
```

Cron example: `0 8 * * * cd /opt/valenciaguard && .venv/bin/python -m app.services.alerts`

## Configuration (.env)

See `.env.example` for all variables: `DATABASE_URL`, `SECRET_KEY`, `UPLOAD_DIR`,
`KIMI_API_KEY` / `KIMI_BASE_URL` / `KIMI_MODEL`, `SMTP_*`, `NOTIFY_EMAIL`,
`CJK_FONT_PATH`, `IRAV_RATE` (default `0.0214`), `COST_THRESHOLD` (default `200`).

- **AI**: without `KIMI_API_KEY` every AI feature (issue triage, contract parsing,
  `/api/ai/ask`) returns sensible canned mock responses.
- **Email**: without `SMTP_HOST` all outgoing mail is logged (`EMAIL STUB ...`)
  instead of sent.
- **Uploads**: only pdf/jpg/jpeg/png, max 10 MB, stored under `UPLOAD_DIR`
  (outside the web root) with randomized filenames; executable magic bytes
  (MZ / ELF / shebang) are rejected.

## Key business logic (LAU)

When a contract is saved, these dates are auto-computed and stored:

- `mandatory_end_date` = start + 5 years (individual landlord) or + 7 years (company)
- `notice_deadline_date` = mandatory end − 4 months (notice before tacit renewal)
- `next_rent_update_date` = next annual rent-update date (if the contract has the clause)
- `tacit_renewal_end_date` = mandatory end + 3 years

Rent increase: `max_increase = current_rent × IRAV_RATE`; the calculator at
`/rent/calculator` generates the Spanish notification letter.

Issues with estimated cost > `COST_THRESHOLD` (€200 default) or high/urgent
urgency trigger a Chinese-language owner notification (stubbed if no SMTP).

## PDF reports and CJK fonts

Monthly owner reports are Chinese PDFs (fpdf2). **A CJK TTF font file is
required** for proper Chinese rendering — install one (e.g.
`fonts-noto-cjk` on Ubuntu) and point `CJK_FONT_PATH` at the `.ttf`/`.ttc`.
If the font is missing the PDF is still generated with a warning banner and
non-Latin characters replaced, so the route never fails.

## Deployment (Ubuntu, systemd + nginx)

```bash
sudo ./install_service.sh
```

The script creates the `valenciaguard` user, installs to `/opt/valenciaguard`,
creates `/var/lib/valenciaguard/uploads`, installs the systemd unit
(`deploy/valenciaguard.service`) and the nginx vhost (`deploy/nginx.conf`),
then prints next steps (edit `.env`, seed, start service, TLS via certbot).

## Password hashing

Uses `hashlib.pbkdf2_hmac` (100k iterations, per-password salt) from the
standard library — chosen because passlib/bcrypt has compatibility issues on
Python 3.14.

## Layout

```
app/
  main.py            dashboard, calendar, settings, app wiring
  models.py          SQLModel models + date/rent math helpers
  database.py        engine/session
  auth.py            hashing, session auth, role guards, CSRF
  audit.py           audit log helper
  config.py          env settings (pydantic-settings)
  routers/           auth, properties, tenants, contracts, rent, issues,
                     documents, owners, ai, portal
  services/          alerts, ai_service, document_parser, notifications, reports
  templates/         admin UI (es) + portal/ (中文) + partials/ (HTMX)
static/style.css
scripts/seed.py      demo data
tests/               pytest suite
deploy/              systemd unit + nginx vhost
install_service.sh   Ubuntu installer
```
