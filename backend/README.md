# FoodStallHub — Backend

FastAPI backend for a food stall marketplace. Relational data (users, stalls, menu
items) lives in **PostgreSQL** via SQLAlchemy; document data (orders, reviews,
analytics) lives in **MongoDB** via PyMongo.

## Architecture

```
backend/
│── app/
│   │── main.py                # FastAPI entry point
│   │── config.py              # Load DB URIs & secrets from .env
│   │── core/
│   │   │── security.py        # JWT, password hashing (bcrypt)
│   │   │── auth.py            # Auth dependencies (current user, roles)
│   │── models/                # SQLAlchemy models (Postgres) + Mongo docs
│   │   │── user.py
│   │   │── stall.py
│   │   │── menu.py
│   │   │── order.py
│   │── schemas/               # Pydantic schemas
│   │   │── user_schema.py
│   │   │── order_schema.py
│   │   │── stall_schema.py
│   │   │── menu_schema.py
│   │   │── review_schema.py
│   │── controllers/           # Route handlers (MVC controllers)
│   │   │── auth_controller.py
│   │   │── user_controller.py
│   │   │── stall_controller.py
│   │   │── menu_controller.py
│   │   │── order_controller.py
│   │   │── review_controller.py
│   │   │── analytics_controller.py
│   │── services/              # Business logic
│   │   │── payment_service.py
│   │   │── delivery_service.py
│   │── repositories/          # DB access layer
│   │   │── postgres_repo.py
│   │   │── mongo_repo.py
│   │── utils/                 # Helpers
│   │   │── logger.py
│   │   │── error_handler.py
│   │── tests/                 # Unit/integration tests
│── .env                       # Secrets (DB URIs, JWT secret)
│── requirements.txt           # Dependencies
│── README.md                  # Documentation
```

## Requirements

- Python 3.11+
- PostgreSQL running locally
- MongoDB running locally

## Setup

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env    # then edit .env with your DB credentials

# Create the databases once:
#   createdb foodstallhub   (PostgreSQL tables auto-create on startup)
```

## Run

```bash
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

PostgreSQL tables are created automatically on startup (`Base.metadata.create_all`).

## Test

Unit tests (no external services required):

```bash
pytest app/tests
```

## API surface (`/api/v1`)

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| POST | `/auth/register` | public | Create customer/vendor account |
| POST | `/auth/login` | public | Get JWT access token |
| GET | `/users/me` | user | Current profile |
| PATCH | `/users/me` | user | Update own profile |
| GET | `/stalls` | public | List stalls (filter/paginate) |
| GET | `/stalls/{id}` | public | Stall detail + rating |
| POST | `/stalls` | vendor/admin | Create a stall |
| PUT/DELETE | `/stalls/{id}` | owner/admin | Update / delete a stall |
| GET | `/stalls/{id}/menu` | public | List menu items |
| POST | `/stalls/{id}/menu` | owner/admin | Add menu item |
| PUT | `/menu/{id}` | owner/admin | Update menu item |
| DELETE | `/menu/{id}` | owner/admin | Delete menu item |
| PATCH | `/menu/{id}/availability` | owner/admin | Toggle availability |
| POST | `/orders` | user | Place an order |
| GET | `/orders/my` | user | My orders |
| GET | `/orders/vendor` | vendor | Orders for my stalls |
| GET | `/orders/{id}` | owner/vendor/admin | Order detail |
| PATCH | `/orders/{id}/status` | vendor/admin | Advance order status |
| POST | `/orders/{id}/cancel` | customer | Cancel pending order |
| POST | `/stalls/{id}/reviews` | customer | Review a delivered order |
| GET | `/stalls/{id}/reviews` | public | Stall reviews + average |
| GET | `/analytics/stalls/{id}/summary` | owner/admin | Orders, revenue, ratings |
| GET | `/analytics/overview` | admin | Platform totals |

## Roles

- `customer` — browse, order, review
- `vendor` — owns stalls, manages menu, fulfils orders
- `admin` — full access, platform analytics

Auth uses a bearer JWT. Example login+request:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","password":"secret1234"}'

curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <token>"
```