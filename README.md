# BrainWise — Logistics Management System

A full-stack logistics management application for managing drivers, delivery orders, delivery runs, delivery stops, and cash collection. Built with **Django REST Framework** (backend) and **React + TypeScript** (frontend), using JWT for stateless authentication and role-based access control.

---

## ERD

![ERD](./images/BrainWise%20(Logistics%20System).png)

---

## Tech Stack

### Backend

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Framework | Django 6.0.7 |
| REST API | Django REST Framework 3.15.2 |
| Authentication | JWT — SimpleJWT 5.3.1 |
| Database | PostgreSQL — psycopg2-binary 2.9.9 |
| Filtering | django-filter 25.1 |
| CORS | django-cors-headers 4.4.0 |
| API Docs | drf-spectacular 0.30.0 (Swagger UI) |
| Environment | python-decouple 3.8 |

### Frontend

| Component | Technology |
|-----------|------------|
| Language | TypeScript 6.0 |
| Framework | React 19.2 |
| Styling | Tailwind CSS 4.3 |
| Routing | React Router DOM 7.18 |
| Data Fetching | TanStack React Query 5.101 |
| Forms | React Hook Form 7.81 |
| HTTP Client | Axios 1.18 |
| Build Tool | Vite 8.1 |

---

## Features

### Authentication & Authorization
- JWT login and token refresh (30 min access / 1 day refresh)
- Role-based access control: **Manager**, **Dispatcher**, **Driver**
- Auto token refresh on frontend

### Driver Management
- Full CRUD with status tracking (AVAILABLE, ON_RUN, INACTIVE)
- Availability filtering, search, ordering
- Max stops per run configuration

### Order Management
- Full CRUD with statuses: OPEN → ASSIGNED → EN_ROUTE → DELIVERED / FAILED / CASH_BANKED
- Priority levels: LOW, MEDIUM, HIGH
- Customer name, address, cash amount tracking

### Delivery Runs
- Build runs from OPEN orders, start runs, complete runs, bank cash
- Full workflow: DRAFT → ASSIGNED → EN_ROUTE → COMPLETED → CASH_BANKED
- Delete guard — only DRAFT runs can be deleted

### Delivery Stops
- Auto-created when a run is built
- Driver can mark stops as DELIVERED or FAILED (with reason)
- Read-only customer fields populated from Order

### Dashboard
- Stats cards: total orders, active drivers, open orders, pending runs
- Recent orders and active runs tables
- Role-specific views

---

## Project Structure

```
BrainWise/
├── backend/                         # Django REST Framework API
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env                         # Environment variables
│   ├── core/                        # Project configuration
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   └── apps/                        # Application modules
│       ├── accounts/                # Authentication & user management
│       │   ├── models.py            # Custom User (roles, timestamps)
│       │   ├── permissions.py       # IsManager, IsDispatcher, IsDriver, IsManagerOrDispatcher
│       │   ├── serializers.py       # UserSerializer, UserCreateSerializer
│       │   ├── tests.py
│       │   └── views.py             # Login, Refresh, Me
│       ├── drivers/                 # Driver management
│       │   ├── models.py            # Driver (OneToOne → User)
│       │   ├── permissions.py       # IsManagerOrDispatcher
│       │   ├── serializers.py       # DriverSerializer (user_data nested on create)
│       │   ├── tests.py
│       │   └── views.py             # DriverViewSet + available action
│       ├── orders/                  # Order management
│       │   ├── models.py            # Order (status, priority, customer)
│       │   ├── permissions.py
│       │   ├── serializers.py
│       │   ├── tests.py
│       │   └── views.py             # OrderViewSet (Manager/Dispatcher only)
│       ├── delivery_runs/           # Delivery run management
│       │   ├── models.py            # DeliveryRun (driver, status)
│       │   ├── permissions.py
│       │   ├── serializers.py
│       │   ├── tests.py
│       │   └── views.py             # DeliveryRunViewSet + build/start/complete/bank actions
│       ├── delivery_stops/          # Delivery stop management
│       │   ├── models.py            # DeliveryStop (run, order, status, driver_name)
│       │   ├── permissions.py       # DeliveryStopPermission (DRIVER_WRITE_ACTIONS)
│       │   ├── serializers.py
│       │   ├── tests.py
│       │   └── views.py             # DeliveryStopViewSet + mark-delivered/mark-failed actions
│       └── common/                  # Shared utilities
│           ├── management/commands/seed_data.py
│           ├── pagination.py        # StandardPagination (page_size=20, max=100)
│           └── exceptions.py        # Custom exception handler
├── frontend/                        # React + TypeScript SPA
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts               # Dev proxy /api → localhost:8000
│   ├── .env                         # VITE_API_URL=http://localhost:8000
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                   # Routes + AuthProvider + QueryClientProvider
│       ├── index.css                 # Tailwind v4 import
│       ├── types/logistics.ts        # All backend type definitions
│       ├── contexts/
│       │   ├── AuthContext.tsx        # JWT auth, auto-refresh, localStorage tokens
│       │   └── ToastContext.tsx       # Toast notifications (success/error)
│       ├── data/api.ts               # Centralized Axios client + all endpoint functions
│       ├── components/
│       │   ├── AppShell.tsx           # Sidebar layout, role-based nav
│       │   ├── ProtectedRoute.tsx     # Auth guard
│       │   └── ui.tsx                 # Reusable UI components
│       └── pages/
│           ├── LoginPage.tsx
│           ├── DashboardPage.tsx
│           ├── DriversPage.tsx
│           ├── OrdersPage.tsx
│           ├── RunsPage.tsx
│           ├── RunDetailsPage.tsx
│           ├── ProfilePage.tsx
│           └── NotFoundPage.tsx
├── seed.sh                          # One-command setup (venv, deps, migrations, seed)
└── images/                          # ERD diagram
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+

### Option 1 — Seed Script (Recommended)

```bash
git clone <repository-url>
cd BrainWise
chmod +x seed.sh
./seed.sh
```

This will:
1. Create a Python virtual environment in `backend/.venv/`
2. Install all Python dependencies
3. Run database migrations
4. Seed the database with demo data

### Option 2 — Manual Setup

#### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in `backend/`:
```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=BrainWise_task
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

```bash
createdb BrainWise_task
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api/ |
| Swagger UI | http://localhost:8000/api/docs/ |
| Django Admin | http://localhost:8000/admin/ |

---

## Seed Data

The `seed_data` command creates:

| Resource | Count | Details |
|----------|-------|---------|
| Users | 10 | 1 manager, 2 dispatchers, 7 drivers |
| Drivers | 7 | All with profiles, statuses, phone numbers |
| Customers | 30 | With names, emails, phone numbers, addresses |
| Orders | 30 | 8 OPEN, 5 ASSIGNED, 4 EN_ROUTE, 6 DELIVERED, 3 FAILED, 4 CASH_BANKED |
| Delivery Runs | 7 | 2 DRAFT, 1 ASSIGNED, 1 EN_ROUTE, 1 COMPLETED, 2 CASH_BANKED |
| Delivery Stops | ~40 | Matching each run's orders with varied statuses |

### Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Manager | manager@brainwise.com | password123 |
| Dispatcher | dispatcher@brainwise.com | password123 |
| Dispatcher | dispatcher2@brainwise.com | password123 |
| Driver | ahmed@brainwise.com | password123 |
| Driver | mona@brainwise.com | password123 |
| Driver | omar@brainwise.com | password123 |
| Driver | layla@brainwise.com | password123 |
| Driver | youssef@brainwise.com | password123 |
| Driver | nour@brainwise.com | password123 |
| Driver | hany@brainwise.com | password123 |
| Driver | dalal@brainwise.com | password123 |

Admin: `admin@brainwise.com` / `admin123`

---

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/login/` | Obtain JWT tokens | No |
| POST | `/api/auth/refresh/` | Refresh access token | No |
| GET | `/api/auth/me/` | Get current user profile | Yes |
| PATCH | `/api/auth/me/` | Update profile | Yes |

### Drivers

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | `/api/drivers/` | List drivers (paginated) | Manager, Dispatcher |
| POST | `/api/drivers/` | Create driver | Manager, Dispatcher |
| GET | `/api/drivers/{id}/` | Retrieve driver | Manager, Dispatcher |
| PUT | `/api/drivers/{id}/` | Full update driver | Manager, Dispatcher |
| PATCH | `/api/drivers/{id}/` | Partial update driver | Manager, Dispatcher |
| DELETE | `/api/drivers/{id}/` | Delete driver | Manager, Dispatcher |
| GET | `/api/drivers/available/` | List available drivers | Manager, Dispatcher |

### Orders

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | `/api/orders/` | List orders (paginated) | Manager, Dispatcher |
| POST | `/api/orders/` | Create order | Manager, Dispatcher |
| GET | `/api/orders/{id}/` | Retrieve order | Manager, Dispatcher |
| PUT | `/api/orders/{id}/` | Full update order | Manager, Dispatcher |
| PATCH | `/api/orders/{id}/` | Partial update order | Manager, Dispatcher |
| DELETE | `/api/orders/{id}/` | Delete order (OPEN only) | Manager, Dispatcher |

### Delivery Runs

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | `/api/delivery-runs/` | List runs (paginated) | Manager, Dispatcher |
| POST | `/api/delivery-runs/` | Create run | Manager, Dispatcher |
| GET | `/api/delivery-runs/{id}/` | Retrieve run | Manager, Dispatcher |
| PUT | `/api/delivery-runs/{id}/` | Full update run | Manager, Dispatcher |
| PATCH | `/api/delivery-runs/{id}/` | Partial update run | Manager, Dispatcher |
| DELETE | `/api/delivery-runs/{id}/` | Delete run (DRAFT only) | Manager, Dispatcher |
| POST | `/api/delivery-runs/{id}/build-run/` | Build run from orders | Manager, Dispatcher |
| POST | `/api/delivery-runs/{id}/start-run/` | Start run | Manager, Dispatcher |
| POST | `/api/delivery-runs/{id}/complete-run/` | Complete run | Manager, Dispatcher |
| POST | `/api/delivery-runs/{id}/bank-cash/` | Bank collected cash | Manager, Dispatcher |

### Delivery Stops

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | `/api/delivery-stops/` | List stops | Manager, Dispatcher, Driver (own) |
| GET | `/api/delivery-stops/{id}/` | Retrieve stop | Manager, Dispatcher, Driver (own) |
| POST | `/api/delivery-stops/{id}/mark-delivered/` | Mark stop delivered | Driver (own) |
| POST | `/api/delivery-stops/{id}/mark-failed/` | Mark stop failed (requires reason) | Driver (own) |

### Query Parameters

All list endpoints support:

| Param | Example | Description |
|-------|---------|-------------|
| `search` | `?search=Ahmed` | Full-text search |
| `ordering` | `?ordering=-created_at` | Sort (prefix `-` for desc) |
| `page` | `?page=2` | Page number |
| `page_size` | `?page_size=50` | Results per page (max 100) |

Orders additionally support `?status=OPEN` and `?priority=HIGH`.

Runs additionally support `?status=DRAFT`.

---

## Role-Based Access Control

| Resource | Manager | Dispatcher | Driver |
|----------|---------|------------|--------|
| Drivers | Full CRUD | Full CRUD | None |
| Orders | Full CRUD | Full CRUD | None |
| Runs | Full CRUD + workflow actions | Build, Start, Bank Cash | None |
| Stops | View all | View all | View own, mark delivered/failed |
| Dashboard | Full stats | Full stats | Personal stats only |

---

## Workflow

### Run Lifecycle

```
DRAFT ──build-run──► ASSIGNED ──start-run──► EN_ROUTE ──complete-run──► COMPLETED ──bank-cash──► CASH_BANKED
```

1. **Build Run**: Select OPEN orders → creates DeliveryRun + DeliveryStops, assigns driver, changes orders to ASSIGNED
2. **Start Run**: Changes run to EN_ROUTE, driver to ON_RUN, orders to EN_ROUTE
3. **Complete Run**: Changes run to COMPLETED, driver to AVAILABLE (only when all stops are DELIVERED or FAILED)
4. **Bank Cash**: Changes run to CASH_BANKED, requires `cash_banked_location`

### Stop Lifecycle

```
PENDING ──mark-delivered──► DELIVERED
PENDING ──mark-failed──────► FAILED (requires failed_reason)
```

---

## Running Tests

```bash
cd backend
source .venv/bin/activate

# All tests
python manage.py test --verbosity=2

# Specific apps
python manage.py test apps.accounts --verbosity=2
python manage.py test apps.drivers --verbosity=2
python manage.py test apps.orders --verbosity=2
python manage.py test apps.delivery_runs --verbosity=2
python manage.py test apps.delivery_stops --verbosity=2

# With existing test DB (faster)
python manage.py test --keepdb --verbosity=2
```

---

## Frontend Commands

```bash
cd frontend

npm run dev       # Start dev server (port 5173)
npm run build     # Production build (tsc + vite)
npm run lint      # ESLint
npm run preview   # Preview production build
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | — | Django secret key |
| `DEBUG` | Yes | — | `True` for dev |
| `DB_NAME` | Yes | — | PostgreSQL database name |
| `DB_USER` | Yes | — | PostgreSQL username |
| `DB_PASSWORD` | Yes | — | PostgreSQL password |
| `DB_HOST` | No | `localhost` | Database host |
| `DB_PORT` | No | `5432` | Database port |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173` | Frontend origins |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## Error Handling

All API errors return a consistent JSON format:

```json
{
  "detail": "Error message here"
}
```

Validation errors return field-specific messages:

```json
{
  "phone_number": ["Phone number is required."],
  "max_stops_per_run": ["max_stops_per_run must be at least 1."]
}
```

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no content) |
| 400 | Bad request / validation error |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |

---

## Branching Strategy

```
main          Production-ready code (stable releases)
  └── dev     Development integration branch
       └── feature/*   Individual feature branches
```

---

## Author

**Ahmed Mazen**
- Portfolio: [Portfolio](https://portfolio-3k2f.vercel.app/)
