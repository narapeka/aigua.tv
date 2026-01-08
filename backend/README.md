# aigua.tv WebUI Backend

FastAPI-based backend for the aigua.tv web interface.

## Features

- **Dry-Run API**: Run organization preview without moving files
- **Job Management**: Track and manage organization jobs with caching
- **Real-time Updates**: WebSocket support for live progress
- **Configuration**: Edit config.yaml via API
- **TMDB Integration**: Search and match shows manually

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Running the Backend

### Development Mode

```bash
cd backend
python -m app.main
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Configuration

### Environment Variables

- `REDIS_URL`: Redis connection URL (optional, defaults to in-memory cache)
  - Example: `redis://localhost:6379`
- `OPENAI_API_KEY`: OpenAI API key (inherited from main project)
- `TMDB_API_KEY`: TMDB API key (inherited from main project)

### Cache Backend

The backend supports two caching modes:

1. **Redis** (Production): Set `REDIS_URL` environment variable
2. **In-Memory** (Development): Automatic fallback if Redis not available

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Jobs
- `POST /api/jobs/dry-run` - Start dry-run
- `GET /api/jobs/{job_id}` - Get job result
- `POST /api/jobs/{job_id}/execute` - Execute organization
- `PUT /api/jobs/{job_id}/shows/{show_id}/select` - Update selection
- `PUT /api/jobs/{job_id}/shows/{show_id}/category` - Update category
- `DELETE /api/jobs/{job_id}` - Delete job

### Configuration
- `GET /api/config` - Get configuration
- `PUT /api/config` - Update configuration
- `GET /api/config/categories` - Get category rules

### TMDB
- `POST /api/tmdb/search` - Search TMDB
- `GET /api/tmdb/show/{tmdb_id}` - Get show details

### WebSocket
- `WS /api/ws/{job_id}` - Real-time progress updates

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── api/routes/          # API endpoints
│   ├── core/                # Core logic (organizer wrapper)
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   └── utils/               # Utilities
└── requirements.txt
```

## Development

### Adding New Endpoints

1. Create route file in `app/api/routes/`
2. Define Pydantic models in `app/models/api_models.py`
3. Add business logic to `app/services/`
4. Include router in `app/main.py`

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test dry-run
curl -X POST http://localhost:8000/api/jobs/dry-run \
  -H "Content-Type: application/json" \
  -d '{"input_dir": "/path/to/input", "output_dir": "/path/to/output"}'
```
