# Logistics Management System API

A backend API for managing logistics operations including driver management, delivery orders, delivery runs, delivery stops, and cash collection. The system enforces role-based access control across three user roles: Manager, Dispatcher, and Driver.

The API is built with Django and Django REST Framework, using JWT for stateless authentication. It is designed to serve as the backend for a logistics company's internal operations, where managers have full system access, dispatchers coordinate deliveries, and drivers execute assigned routes.

This repository contains the backend only. The frontend is a separate React application that consumes this API.

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Framework | Django 6.0.7 |
| REST API | Django REST Framework 3.15.2 |
| Authentication | JWT via djangorestframework-simplejwt 5.3.1 |
| Database | PostgreSQL (via psycopg2-binary 2.9.9) |
| CORS | django-cors-headers 4.4.0 |
| Environment | python-decouple 3.8 |

---

## Features

### Authentication (Implemented)

- JWT login (access + refresh tokens)
- Token refresh endpoint
- Current user retrieval and profile update
- Role-based access control (Manager, Dispatcher, Driver)

### Driver Management (Planned)

- CRUD operations for driver profiles
- Driver availability validation
- Assign/unassign drivers to delivery runs

### Order Management (Planned)

- CRUD operations for delivery orders
- Order status tracking (Open, Assigned, En Route, Delivered, Failed)
- Order-to-driver assignment

### Delivery Runs (Planned)

- Build a delivery run from multiple orders
- Start and complete a run
- Bank collected cash after run completion

### Delivery Stops (Planned)

- Deliver individual stops within a run
- Handle failed stops with reason tracking
- Validate stop completion before run completion

### Dashboard (Planned)

- Real-time overview of active runs
- Driver status summary
- Order completion metrics

---

## Project Structure

```
backend/
├── manage.py
├── requirements.txt
├── .env
├── core/
│   ├── __init__.py
│   ├── settings.py          # Django settings, JWT config, CORS, DB
│   ├── urls.py              # Root URL configuration
│   ├── asgi.py
│   └── wsgi.py
└── apps/
    ├── __init__.py
    └── accounts/
        ├── __init__.py
        ├── admin.py          # User admin registration
        ├── apps.py           # App configuration
        ├── managers.py       # Custom UserManager
        ├── models.py         # User model, RoleChoices
        ├── permissions.py    # Role-based permission classes
        ├── serializers.py    # User serializer
        ├── tests.py          # 100 test cases
        ├── urls.py           # Auth URL routes
        ├── views.py          # MeView (GET/PATCH profile)
        └── migrations/
            ├── __init__.py
            └── 0001_initial.py
```

All Django apps are organized under the `apps/` directory to keep the project root clean and to clearly separate application code from project configuration (`core/`).

---

## Database Design

The system uses the following core entities:

### User (accounts.User)

Extends Django's `AbstractUser` with a `role` field and a unique `email`.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key |
| username | CharField(150) | Unique, used for login |
| email | EmailField | Unique |
| role | CharField(20) | MANAGER, DISPATCHER, or DRIVER |
| first_name | CharField(150) | Optional |
| last_name | CharField(150) | Optional |
| is_active | BooleanField | Deactivation instead of deletion |
| date_joined | DateTimeField | Auto-set on creation |

### Planned Entities

- **Driver** -- Profile linked to a User with role=DRIVER. Tracks vehicle info, availability, and max stops per run.
- **Order** -- A delivery order with pickup/dropoff addresses, customer info, and status.
- **Delivery Run** -- A collection of orders assigned to a driver for a single route.
- **Delivery Stop** -- A single stop within a run, linked to one order, with delivery status and cash collection.

---

## Run Lifecycle

The business workflow for a delivery run follows these states:

```
Open Order
    ↓  (Assigned to a driver)
Assigned
    ↓  (Driver starts the run)
En Route
    ↓  (All stops delivered or failed)
Delivered / Failed
    ↓  (Cash collected is deposited)
Cash Banked
```

Each transition enforces specific validations:

- **Assign**: Order must be Open; driver must be active and not already on a run.
- **Start**: All orders in the run must be assigned; driver must be available.
- **Deliver Stop**: Stop must belong to an active run; driver must own the run.
- **Complete Run**: All stops must be in a terminal state (Delivered or Failed).
- **Bank Cash**: Run must be completed; cash amount must match collected total.

---

## Role-Based Access Control

| Role | Permissions |
|------|------------|
| **Manager** | Full access to all resources. Can manage users, drivers, orders, runs, and view reports. |
| **Dispatcher** | Manage drivers and orders. Build and start delivery runs. Cannot complete runs or bank cash. |
| **Driver** | View assigned delivery stops. Update stop status for their own runs only. Cannot access other resources. |

Permission classes are implemented in `apps/accounts/permissions.py`:

- `IsManager` -- Allows access only to users with role=MANAGER
- `IsDispatcher` -- Allows access only to users with role=DISPATCHER
- `IsDriver` -- Allows access only to users with role=DRIVER

All permission classes require the user to be authenticated.

---

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/login/` | Obtain JWT access + refresh tokens | No |
| POST | `/api/auth/refresh/` | Refresh an expired access token | No |
| GET | `/api/auth/me/` | Retrieve current user profile | Yes |
| PATCH | `/api/auth/me/` | Update current user profile (first_name, last_name) | Yes |

### Admin

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/admin/` | Django admin panel | Yes (staff) |

---

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- pip

### Steps

```bash
# Clone the repository
git clone <repository-url>
cd BrainWise/backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your database credentials and secret key

# Run database migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

The API will be available at `http://localhost:8000/`.

---

## Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key for cryptographic signing | Yes |
| `DEBUG` | Set to `True` for development, `False` for production | Yes |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames | No (defaults to `localhost,127.0.0.1`) |
| `DB_NAME` | PostgreSQL database name | Yes |
| `DB_USER` | PostgreSQL database user | Yes |
| `DB_PASSWORD` | PostgreSQL database password | Yes |
| `DB_HOST` | PostgreSQL database host | No (defaults to `localhost`) |
| `DB_PORT` | PostgreSQL database port | No (defaults to `5432`) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins | No (defaults to `http://localhost:5173`) |

### Example `.env`

```
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

---

## Authentication

The API uses JWT (JSON Web Token) authentication via SimpleJWT.

### Token Lifetimes

| Token | Lifetime |
|-------|----------|
| Access token | 30 minutes |
| Refresh token | 1 day |

### Authentication Flow

```
1. POST /api/auth/login/  →  Receive access + refresh tokens
2. Include access token in Authorization header for protected endpoints
3. When access token expires, POST /api/auth/refresh/ with refresh token
4. Use the new access token for subsequent requests
```

### Authorization Header

All protected endpoints require the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Example: Login

```http
POST /api/auth/login/
Content-Type: application/json

{
    "username": "logistics_manager",
    "password": "Bw@Secure123!"
}
```

Response:

```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIs...",
    "access": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Example: Access Protected Endpoint

```http
GET /api/auth/me/
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Response:

```json
{
    "id": 1,
    "username": "logistics_manager",
    "email": "manager@brainwise.com",
    "first_name": "Ahmed",
    "last_name": "Hassan",
    "role": "MANAGER",
    "date_joined": "2026-07-09T17:04:00Z"
}
```

---

## Validation and Business Rules

### User Model

- Email is required and must be unique
- Password is required at creation time
- Email domain is normalized to lowercase (per RFC 5321)
- Default role is DRIVER if not specified

### Role-Based Rules

- Only Managers can create or delete users
- Only Dispatchers and Managers can assign drivers to runs
- Drivers can only update stops assigned to their own runs
- Inactive drivers cannot be assigned to new runs
- A driver cannot be on multiple active runs simultaneously

### Planned Business Rules

- Driver max stops must be greater than zero
- Cash amount cannot be negative
- Only Open orders can be assigned to a run
- All stops must be completed before a run can be marked complete
- Cash banked amount must match the total collected from delivered stops

---

## Assumptions

- Users are created by administrators through Django admin. There is no public registration endpoint. This is an internal logistics system, not a consumer-facing application.
- Authentication uses JWT with stateless token validation. Tokens are not blacklisted; they expire naturally after their configured lifetime.
- PostgreSQL is the primary database. No other database backends are supported.
- The system uses Africa/Cairo as the default timezone.
- The frontend runs separately on port 5173 (Vite dev server) and communicates with this API via CORS-configured origins.

---

## Testing

The project includes 100 automated test cases covering:

- User model creation, validation, and string representation
- Serializer field exposure and read-only enforcement
- Role-based permission classes (IsManager, IsDispatcher, IsDriver)
- JWT login, token refresh, and token validation
- Protected endpoint access (authenticated and unauthenticated)
- HTTP method restrictions on all endpoints
- Edge cases (malformed requests, empty bodies, concurrent token usage)
- Admin panel accessibility

### Running Tests

```bash
python manage.py test apps.accounts --verbosity=2
```

---

## Future Improvements

- Docker and Docker Compose support for containerized deployment
- CI/CD pipeline (GitHub Actions)
- Token blacklisting and logout endpoint
- API rate limiting to prevent brute-force attacks
- Audit logging for all data mutations
- Email notifications for delivery status changes
- Background task processing with Celery
- API documentation with DRF Spectacular (OpenAPI/Swagger)
- Monitoring and structured logging
- Pagination, filtering, and search across list endpoints

---

## Author

**Mazen**
- GitHub: [mazen](https://github.com/mazen)
