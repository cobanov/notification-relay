# Notification Relay

FastAPI server to receive and store notifications from mobile devices.

## Quick Start

```bash
docker-compose up -d
```

**Access:**
- API: `http://localhost:4141`
- Database: `localhost:4142`
- Dashboard: `http://localhost:4141/dashboard` (password = `API_KEY`)

## Configuration

Create `.env`:

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=notifications

# API
API_KEY=your-secret-key

# Optional
DEBUG=false
LOG_LEVEL=INFO
```

## API Usage

**Create Notification**

```bash
curl -X POST http://localhost:4141/notifications \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{
    "app_name": "WhatsApp",
    "title": "New Message",
    "text": "Hello!"
  }'
```

**Dashboard**

- Go to `/dashboard`
- Enter the **same value** as your `X-API-Key` / `API_KEY` (no username)

**Health Check**

```bash
curl http://localhost:4141/health
```

## Development

```bash
# Install
uv sync

# Run
uv run uvicorn app.main:app --reload --port 8000

# View logs
docker-compose logs -f api
```

## Features

- Async PostgreSQL with SQLAlchemy
- API key authentication
- Automatic JSON sanitization for mobile apps
- Structured logging
- Health checks
- Docker optimized with uv

## Stack

FastAPI · PostgreSQL · SQLAlchemy · Docker · uv
