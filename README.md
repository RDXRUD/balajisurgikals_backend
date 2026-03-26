# Balaji Surgikals — Backend

FastAPI backend for the Balaji Surgikals e-commerce platform.

## Tech Stack

- FastAPI
- Uvicorn (ASGI server)
- MongoDB Atlas + Motor (async driver)
- Pydantic v2
- python-jose (JWT auth)
- passlib / bcrypt (password hashing)
- boto3 (OCI Object Storage via S3-compatible API)

## Prerequisites

- Python >= 3.12
- MongoDB Atlas cluster
- Oracle Cloud (OCI) Object Storage bucket (for image uploads)

## Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your MongoDB URI, JWT secret, and OCI credentials

# 5. Start the server
uvicorn main:app --reload --port 8000
```

API runs at http://localhost:8000  
Swagger docs at http://localhost:8000/docs

## Environment Variables

| Variable | Description |
|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `MONGODB_DB` | Database name |
| `JWT_SECRET` | Secret key for signing JWT tokens |
| `JWT_ALGORITHM` | Algorithm (default: HS256) |
| `JWT_EXPIRE_MINUTES` | Token expiry in minutes |
| `ADMIN_EMAIL` | Admin account email (seeded on startup) |
| `ADMIN_PASSWORD` | Admin account password (seeded on startup) |
| `OCI_NAMESPACE` | OCI Object Storage namespace |
| `OCI_REGION` | OCI region (e.g. ap-mumbai-1) |
| `OCI_BUCKET` | OCI bucket name |
| `OCI_ACCESS_KEY` | OCI Customer Secret Key (access) |
| `OCI_SECRET_KEY` | OCI Customer Secret Key (secret) |

## Project Structure

```
backend/
├── routers/        # Route handlers (auth, products, orders, etc.)
├── main.py         # App entry point & startup
├── models.py       # Pydantic models
├── database.py     # MongoDB connection
├── auth.py         # JWT auth utilities
├── config.py       # Settings via pydantic-settings
├── storage.py      # OCI object storage client
└── requirements.txt
```

## API Routes

| Prefix | Description |
|---|---|
| `/auth` | Login, register, token refresh |
| `/products` | Product CRUD |
| `/orders` | Order management |
| `/customers` | Customer management |
| `/analytics` | Sales analytics |
| `/promotions` | Promotions & discounts |
| `/wishlist` | User wishlist |
