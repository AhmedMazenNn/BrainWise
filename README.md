# Logistics Management System API

A backend API for managing logistics operations including driver management, delivery orders, delivery runs, delivery stops, and cash collection. The system enforces role-based access control across three user roles: Manager, Dispatcher, and Driver.

Built with Django 6.0.7 and Django REST Framework, using JWT for stateless authentication. Designed to serve as the backend for a logistics company's internal operations.

This repository contains the backend only. The frontend is a separate React application.

---

## ERD
![ERD](./images/BrainWise%20(Logistics%20System).png)

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Framework | Django 6.0.7 |
| REST API | Django REST Framework 3.15.2 |
| Authentication | JWT (SimpleJWT 5.3.1) |
| Database | PostgreSQL (psycopg2-binary 2.9.9) |
| Filtering | django-filter 25.1 |
| CORS | django-cors-headers 4.4.0 |
| Environment | python-decouple 3.8 |

---

## Features

### Implemented

- **Authentication** -- JWT login, token refresh, profile retrieval/update
- **Role-Based Access Control** -- Manager, Dispatcher, Driver roles with granular permissions
- **Driver Management** -- Full CRUD, status tracking, availability filtering, search, ordering

### Planned

- Order Management
- Delivery Runs
- Delivery Stops
- Dashboard & Reporting

---

## Project Structure

```
backend/
├── manage.py
├── requirements.txt
├── .env
├── core/                        # Project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── apps/                        # Application modules
    ├── __init__.py
    ├── accounts/                # Authentication & user management
    │   ├── admin.py
    │   ├── apps.py
    │   ├── managers.py
    │   ├── models.py
    │   ├── permissions.py
    │   ├── serializers.py
    │   ├── tests.py             # 100 tests
    │   ├── urls.py
    │   ├── views.py
    │   └── migrations/
    └── drivers/                 # Driver management
        ├── admin.py
        ├── apps.py
        ├── models.py
        ├── permissions.py
        ├── serializers.py
        ├── services.py
        ├── tests.py             # 99 tests
        ├── urls.py
        ├── validators.py
        ├── views.py
        └── migrations/
```

---

## Branching Strategy

```
main          Production-ready code (stable releases)
  └── dev     Development integration branch
       └── feature/*   Individual feature branches
```

### Workflow

1. Create a feature branch from `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/feature-name
   ```

2. Work on the feature, commit changes:
   ```bash
   git add .
   git commit -m "feat: add feature description"
   ```

3. Push and create a Pull Request to `dev`:
   ```bash
   git push origin feature/feature-name
   ```
   Then open a PR on GitHub targeting the `dev` branch for review and testing.

4. After testing and approval, merge into `dev`:
   ```
   feature/feature-name  →  dev
   ```

5. Periodically merge `dev` into `main` for production releases:
   ```
   dev  →  main
   ```

### Current Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production — stable, tested releases |
| `dev` | Development — integration branch for testing |
| `feature/auth` | Authentication module (completed) |
| `feature/drivers` | Driver management module (completed) |

---

## Setup & Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- pip

### 1. Clone the Repository

```bash
git clone <repository-url>
cd BrainWise
```

### 2. Switch to the Development Branch

```bash
git checkout dev
```

### 3. Create and Activate a Virtual Environment

```bash
cd backend
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=BrainWise_task
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

CORS_ALLOWED_ORIGINS=http://localhost:5173
```

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | `True` for dev, `False` for production | Yes |
| `ALLOWED_HOSTS` | Comma-separated allowed hostnames | No |
| `DB_NAME` | PostgreSQL database name | Yes |
| `DB_USER` | PostgreSQL username | Yes |
| `DB_PASSWORD` | PostgreSQL password | Yes |
| `DB_HOST` | Database host | No (default: `localhost`) |
| `DB_PORT` | Database port | No (default: `5432`) |
| `CORS_ALLOWED_ORIGINS` | Frontend origins | No (default: `http://localhost:5173`) |

### 6. Create the Database

```bash
# Using psql
psql -U postgres
CREATE DATABASE "BrainWise_task";
\q
```

### 7. Run Migrations

```bash
python manage.py migrate
```

### 8. Create a Superuser

```bash
python manage.py createsuperuser
```

### 9. Start the Development Server

```bash
python manage.py runserver
```

The API is available at `http://localhost:8000/`.

---

## Running Tests

### All Tests (Both Apps)

```bash
python manage.py test --verbosity=2
```

### Accounts App Only (100 tests)

```bash
python manage.py test apps.accounts --verbosity=2
```

### Drivers App Only (99 tests)

```bash
python manage.py test apps.drivers --verbosity=2
```

### With Existing Test Database

```bash
python manage.py test --keepdb --verbosity=2
```

---

## Authentication

JWT-based stateless authentication via SimpleJWT.

### Token Lifetimes

| Token | Lifetime |
|-------|----------|
| Access | 30 minutes |
| Refresh | 1 day |

### Flow

```
1. POST /api/auth/login/       →  Get access + refresh tokens
2. Use access token in Authorization header
3. POST /api/auth/refresh/     →  Get new access token when expired
```

### Headers

All protected endpoints require:

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/login/` | Obtain JWT tokens | No |
| POST | `/api/auth/refresh/` | Refresh access token | No |
| GET | `/api/auth/me/` | Get current user profile | Yes |
| PATCH | `/api/auth/me/` | Update profile (first_name, last_name) | Yes |

### Drivers

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | `/api/drivers/` | List all drivers (paginated) | Manager, Dispatcher |
| POST | `/api/drivers/` | Create a driver | Manager, Dispatcher |
| GET | `/api/drivers/{id}/` | Retrieve a driver | Manager, Dispatcher |
| PUT | `/api/drivers/{id}/` | Full update a driver | Manager, Dispatcher |
| PATCH | `/api/drivers/{id}/` | Partial update a driver | Manager, Dispatcher |
| DELETE | `/api/drivers/{id}/` | Delete a driver | Manager, Dispatcher |
| GET | `/api/drivers/available/` | List available drivers only | Manager, Dispatcher |

### Drivers Query Parameters

| Param | Example | Description |
|-------|---------|-------------|
| `status` | `?status=AVAILABLE` | Filter by status (AVAILABLE, ON_RUN, INACTIVE) |
| `active` | `?active=true` | Filter by active flag (true, false) |
| `search` | `?search=Ahmed` | Search by name or phone_number |
| `ordering` | `?ordering=name` | Sort by name or created_at (prefix with `-` for descending) |
| `page` | `?page=2` | Page number for pagination |
| `page_size` | `?page_size=50` | Results per page (max 100, default 20) |

---

## Role-Based Access Control

| Role | Drivers | Orders | Runs | Stops | Dashboard |
|------|---------|--------|------|-------|-----------|
| **Manager** | Full CRUD | Full CRUD | Full CRUD | Full CRUD | Full Access |
| **Dispatcher** | Full CRUD | Full CRUD | Build & Start | View | Limited |
| **Driver** | No Access | No Access | No Access | View & Update Own | No Access |

### Permission Classes

| Class | Location | Description |
|-------|----------|-------------|
| `IsManager` | `apps/accounts/permissions.py` | Allows MANAGER role only |
| `IsDispatcher` | `apps/accounts/permissions.py` | Allows DISPATCHER role only |
| `IsDriver` | `apps/accounts/permissions.py` | Allows DRIVER role only |
| `IsManagerOrDispatcher` | `apps/drivers/permissions.py` | Allows MANAGER or DISPATCHER roles |

---

## Driver Management Module

### Model Fields

| Field | Type | Constraints |
|-------|------|-------------|
| `user` | OneToOneField(User) | CASCADE, unique |
| `name` | CharField(255) | Required |
| `phone_number` | CharField(20) | Required, validated format |
| `active` | BooleanField | Default: True |
| `max_stops_per_run` | PositiveIntegerField | Default: 1, must be >= 1 |
| `status` | CharField(TextChoices) | Default: AVAILABLE |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-updated on save |

### Status Choices

| Value | Label | Description |
|-------|-------|-------------|
| `AVAILABLE` | Available | Driver is ready for assignment |
| `ON_RUN` | On Run | Driver is currently on a delivery run |
| `INACTIVE` | Inactive | Driver is not available for work |

### Validation Rules

- **Phone number** -- Required, must match format `+?[\d\s\-()]{7,20}`
- **max_stops_per_run** -- Must be >= 1
- **Status** -- Must be one of AVAILABLE, ON_RUN, INACTIVE
- **Active + ON_RUN** -- A driver cannot be inactive while their status is ON_RUN

---

## Example Requests

### Login

```http
POST /api/auth/login/
Content-Type: application/json

{
    "username": "admin_user",
    "password": "admin_pass"
}
```

**Response (200):**
```json
{
    "access": "eyJhbGciOiJIUzI1NiIs...",
    "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Create Driver

```http
POST /api/drivers/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "user": 5,
    "name": "Ahmed Mohamed",
    "phone_number": "+201234567890",
    "active": true,
    "max_stops_per_run": 8,
    "status": "AVAILABLE"
}
```

**Response (201):**
```json
{
    "id": 1,
    "user": 5,
    "name": "Ahmed Mohamed",
    "phone_number": "+201234567890",
    "active": true,
    "max_stops_per_run": 8,
    "status": "AVAILABLE",
    "created_at": "2026-07-10T19:33:00Z",
    "updated_at": "2026-07-10T19:33:00Z"
}
```

### List Drivers with Filters

```http
GET /api/drivers/?status=AVAILABLE&search=Ahmed&ordering=name
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "user": 5,
            "name": "Ahmed Mohamed",
            "phone_number": "+201234567890",
            "active": true,
            "max_stops_per_run": 8,
            "status": "AVAILABLE",
            "created_at": "2026-07-10T19:33:00Z",
            "updated_at": "2026-07-10T19:33:00Z"
        }
    ]
}
```

### Available Drivers

```http
GET /api/drivers/available/
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
    "count": 3,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "user": 5,
            "name": "Ahmed Mohamed",
            "phone_number": "+201234567890",
            "active": true,
            "max_stops_per_run": 8,
            "status": "AVAILABLE",
            "created_at": "2026-07-10T19:33:00Z",
            "updated_at": "2026-07-10T19:33:00Z"
        }
    ]
}
```

### Validation Error

**Response (400):**
```json
{
    "phone_number": ["Phone number is required."],
    "max_stops_per_run": ["max_stops_per_run must be at least 1."],
    "status": ["A driver cannot be inactive while their status is ON_RUN."]
}
```

### Forbidden (Driver Role)

**Response (403):**
```json
{
    "detail": "You do not have permission to perform this action."
}
```

### Unauthorized

**Response (401):**
```json
{
    "detail": "Given token not valid for any token type"
}
```

---

## Admin Panel

The Django admin panel is available at `/admin/`.

### Driver Admin Configuration

| Setting | Value |
|---------|-------|
| `list_display` | id, name, phone_number, status, active, max_stops_per_run, created_at |
| `list_filter` | status, active |
| `search_fields` | name, phone_number |
| `ordering` | -created_at |
| `raw_id_fields` | user |
| `readonly_fields` | created_at, updated_at |

---

## Assumptions

- Users are created by administrators through Django admin. There is no public registration endpoint.
- JWT tokens are stateless — no blacklisting; they expire naturally.
- PostgreSQL is the only supported database backend.
- Default timezone is Africa/Cairo.
- The frontend runs on port 5173 (Vite dev server) and communicates via CORS.
- The `driver_profile` related name on User allows accessing the driver profile via `user.driver_profile`.

---

## Error Handling

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no content) |
| 400 | Bad request / validation error |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 405 | Method not allowed |

All error responses include a `detail` field or field-specific error messages in JSON format.

---

## Future Improvements

- Docker and Docker Compose for containerized deployment
- CI/CD pipeline (GitHub Actions)
- Token blacklisting and logout endpoint
- API rate limiting
- Audit logging for all data mutations
- Background task processing with Celery
- API documentation with DRF Spectacular (OpenAPI/Swagger)
- Monitoring and structured logging

---

## Author

**Ahmed Mazen**
- Portfolio: [Portfolio](https://portfolio-3k2f.vercel.app/)

