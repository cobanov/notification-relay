# Notification Relay

FastAPI server to receive and store notifications from mobile devices.

## Quick Start

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api
```

API available at: `http://localhost:4141`  
Database available at: `localhost:4142`

## Environment Variables

Create `.env` file:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=notifications
API_KEY=your-secret-key
ALLOWED_ORIGINS=*
```

## API Endpoints

### `POST /notifications`

Store a notification. Requires `X-API-Key` header.

```bash
curl -X POST http://localhost:4141/notifications \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{
    "app_name": "WhatsApp",
    "title": "New Message",
    "text": "Hello!",
    "timestamp": "2024-12-12T10:00:00"
  }'
```

### `GET /health`

Health check endpoint.

### `GET /`

API status and version.

## Development

```bash
# Install dependencies
uv sync

# Run locally
uv run uvicorn app.main:app --reload --port 8000
```

## Tech Stack

- FastAPI
- PostgreSQL
- SQLAlchemy (async)
- Docker + uv
