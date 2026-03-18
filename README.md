# Budgy — Purchase & Budget Tracker

A production-ready internal web application for a K12 school district technology department to track purchases against budget line items, with fiscal-year-aware dashboard and reporting.

## Architecture

```
app/
├── __init__.py          # Application factory, extension setup
├── config/settings.py   # Dev/Prod/Test configuration classes
├── models/              # SQLAlchemy models (User, Purchase, Document, etc.)
├── routes/              # Flask blueprints (dashboard, purchases, budget, documents)
├── admin/routes.py      # Admin blueprint with full CRUD
├── auth/routes.py       # Microsoft Entra ID SSO + dev login fallback
├── services/            # Business logic (fiscal year, budget calculations, storage)
├── utils/               # Decorators (role_required), WTForms
├── templates/           # Jinja2 templates (Bootstrap 5)
├── static/              # CSS/JS/images
├── cli.py               # Flask CLI commands (seed)
migrations/              # Alembic migrations
tests/                   # pytest test suite
```

**Stack:** Flask · PostgreSQL · SQLAlchemy · Alembic · Bootstrap 5 · Gunicorn · Docker

**Key patterns:**
- Application factory (`create_app()`)
- Blueprints for route organization
- Service layer for business logic
- Storage abstraction (local filesystem / Cloudflare R2)
- Role-based access control (admin, manager, staff)
- CSRF protection via Flask-WTF
- ProxyFix for reverse proxy deployment

## Setup

### Prerequisites
- Docker & Docker Compose

### Local Development

1. **Clone and configure:**
   ```bash
   cp .env.example .env
   # Edit .env — set SECRET_KEY, ADMIN_EMAILS
   # Leave AZURE_CLIENT_ID empty to use dev login
   ```

2. **Start services:**
   ```bash
   docker compose up --build
   ```
   This will:
   - Start PostgreSQL
   - Run Alembic migrations
   - Seed default budget line items and current fiscal year
   - Start the app on http://localhost:5000

3. **First login:**
   - With Azure AD unconfigured, you'll see the dev login form
   - Enter an email listed in `ADMIN_EMAILS` to get admin access
   - Subsequent users get `staff` role by default

4. **Run tests:**
   ```bash
   docker compose exec app python -m pytest tests/ -v
   ```

### Running Migrations

```bash
# Inside the container
flask db upgrade          # Apply all migrations
flask db migrate -m "msg" # Generate new migration
flask db downgrade        # Roll back one migration
```

### Seed Data

```bash
flask seed run
```

Creates:
- 9 default budget line items (72250 336, 72250 470, etc.)
- Current fiscal year
- Zero-amount allocations for all line items

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `dev-secret-change-me` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://budgy:budgy@db:5432/budgy` |
| `FLASK_ENV` | `development` or `production` | `development` |
| `ADMIN_EMAILS` | Comma-separated admin emails | (empty) |
| `AZURE_CLIENT_ID` | Entra ID app client ID | (empty = dev login) |
| `AZURE_CLIENT_SECRET` | Entra ID app client secret | |
| `AZURE_TENANT_ID` | Entra ID tenant ID | |
| `AZURE_REDIRECT_URI` | OAuth callback URL | `http://localhost:5000/auth/callback` |
| `STORAGE_BACKEND` | `local` or `r2` | `local` |
| `LOCAL_UPLOAD_PATH` | Local upload directory | `uploads` |
| `R2_ACCOUNT_ID` | Cloudflare account ID | |
| `R2_ACCESS_KEY_ID` | R2 access key | |
| `R2_SECRET_ACCESS_KEY` | R2 secret key | |
| `R2_BUCKET_NAME` | R2 bucket name | |
| `R2_ENDPOINT_URL` | R2 S3-compatible endpoint | |
| `MAX_UPLOAD_SIZE_MB` | Max upload size | `25` |
| `PREFERRED_URL_SCHEME` | `http` or `https` | `http` |
| `APP_URL` | Application base URL | `http://localhost:5000` |

## Microsoft Entra ID SSO Configuration

1. **Register an app** in Azure Portal → App registrations
2. Set **Redirect URI** to `https://your-domain.com/auth/callback` (Web platform)
3. Create a **client secret**
4. Under **API permissions**, add `User.Read` (Microsoft Graph, delegated)
5. Grant admin consent
6. Set environment variables:
   ```
   AZURE_CLIENT_ID=<Application (client) ID>
   AZURE_CLIENT_SECRET=<Client secret value>
   AZURE_TENANT_ID=<Directory (tenant) ID>
   AZURE_REDIRECT_URI=https://your-domain.com/auth/callback
   ```

**Admin bootstrap:** The first user whose email matches `ADMIN_EMAILS` gets `admin` role automatically. Subsequent role management is done in the admin UI.

## Cloudflare R2 Configuration

1. **Create an R2 bucket** in the Cloudflare dashboard
2. **Create API tokens** with read/write access to the bucket
3. Set environment variables:
   ```
   STORAGE_BACKEND=r2
   R2_ACCOUNT_ID=<your-account-id>
   R2_ACCESS_KEY_ID=<your-access-key>
   R2_SECRET_ACCESS_KEY=<your-secret-key>
   R2_BUCKET_NAME=budgy-uploads
   R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
   ```

**Object key structure:** `uploads/{fiscal_year}/{purchase_id}/{uuid}_{filename}`

**Access pattern:** Files are served through the application (server-mediated). The app downloads from R2 and streams to the user. No public bucket URLs are exposed.

**CORS:** Not required unless you plan to serve files directly from R2 (not recommended for this app).

## File Upload Storage

- **Development:** Files stored in `uploads/` directory (local filesystem)
- **Production:** Files stored in Cloudflare R2
- **Abstraction layer:** `app/services/storage.py` provides `LocalStorage` and `R2Storage` implementations behind a common `StorageBackend` interface
- **Metadata:** File metadata (name, size, type, object key) stored in `documents` table
- **Allowed types:** PDF, JPG, JPEG, PNG
- **Size limit:** Configurable via `MAX_UPLOAD_SIZE_MB`
- **Access control:** Files served through authenticated routes with role checks

## Reverse Proxy / Cloudflare Tunnel Deployment

### Flask Configuration
The app uses `werkzeug.middleware.proxy_fix.ProxyFix` to correctly handle:
- `X-Forwarded-For` (client IP)
- `X-Forwarded-Proto` (HTTPS detection)
- `X-Forwarded-Host` (correct URL generation)

### Production Settings
```
FLASK_ENV=production
PREFERRED_URL_SCHEME=https
SECRET_KEY=<strong-random-key>
```

Session cookies are set with `Secure=True` and `HttpOnly=True` in production.

### Cloudflare Tunnel Setup
1. Install `cloudflared` on the server
2. Create a tunnel: `cloudflared tunnel create budgy`
3. Configure the tunnel to point to `http://localhost:8000` (the Gunicorn port)
4. Route DNS to the tunnel
5. Set `AZURE_REDIRECT_URI` to `https://your-tunnel-domain.com/auth/callback`

**Do not** terminate TLS in Flask. Cloudflare handles TLS at the edge.

### Docker Production Deployment

```bash
# Build
docker compose -f docker-compose.yml build

# Start (production would typically use a separate compose file
# without volume mounts and with proper secrets management)
docker compose up -d
```

For production, consider:
- External PostgreSQL (managed database)
- Container orchestration (Docker Swarm, K8s)
- Secrets management (not .env files)
- Log aggregation
- Backup strategy for the database

## Fiscal Year Logic

- Fiscal year runs **July 1 through June 30**
- A purchase dated August 15, 2025 → FY 2025-2026
- A purchase dated March 1, 2026 → FY 2025-2026
- A purchase dated June 30, 2026 → FY 2025-2026
- A purchase dated July 1, 2026 → FY 2026-2027
- Dashboard calculations are scoped to the selected fiscal year
- Budget allocations are per fiscal year per line item
- Remaining = Allocated − Approved spend
- Pending spend (submitted/reviewed) shown separately

## Roles

| Role | Permissions |
|------|-------------|
| **staff** | Create purchases, upload receipts, view own purchases |
| **manager** | View all purchases, dashboard, budget reports, update purchase status |
| **admin** | Full CRUD on all entities, user management, budget allocations |

## Assumptions Made

1. **Single-tenant:** The app serves one school district; no multi-tenancy needed.
2. **File serving:** Files are served through the application (not direct R2 URLs) for access control.
3. **No email notifications:** Purchase status changes don't trigger emails (could be added).
4. **Budget allocations start at $0:** When a fiscal year is created, allocations are initialized to $0; admins update them.
5. **Dev login:** When `AZURE_CLIENT_ID` is empty, a simple email-based dev login is available (no password).
6. **Fiscal year auto-creation:** If a purchase date falls in a fiscal year that doesn't exist, one is created automatically.
7. **Single approval workflow:** Purchases go through submitted → reviewed → approved/rejected. No multi-level approvals.
8. **Time zone:** Fiscal year dates use naive dates (date only, no time zone). Server time is used for timestamps.
