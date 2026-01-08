# aigua.tv WebUI - Complete Installation & Usage Guide

## Overview

The aigua.tv WebUI provides a modern web interface for organizing TV show libraries. It consists of:
- **Backend**: FastAPI server with REST API and WebSocket support
- **Frontend**: React + TypeScript SPA with Material-UI

## Quick Start

### Prerequisites

- Python 3.7+ (for backend)
- Node.js 16+ and npm (for frontend)
- OpenAI API key or compatible LLM service
- TMDB API key
- (Optional) Redis for production caching

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Configure API Keys

Edit `config.yaml` in the root directory:

```yaml
llm:
  api_key: "your-openai-api-key"
  base_url: null  # or custom URL for compatible APIs
  model: "gpt-4o-mini"
  batch_size: 50
  rate_limit: 2

tmdb:
  api_key: "your-tmdb-api-key"
  languages:
    - "zh-CN"
    - "zh-TW"
    - "en-US"
  rate_limit: 40
```

### 4. Start the Backend

```bash
cd backend
python -m app.main
```

Backend runs at **http://localhost:8000**

Visit http://localhost:8000/docs for API documentation

### 5. Start the Frontend

```bash
cd frontend
npm run dev
```

Frontend runs at **http://localhost:5173**

## Usage Workflow

### Step 1: Start Dry-Run

1. Open http://localhost:5173 in your browser
2. Enter input directory (where your TV shows are)
3. Enter output directory (where to organize them)
4. Click "Start Dry-Run"

The system will:
- Scan all folders in the input directory
- Use LLM to extract TV show names (Chinese & English)
- Fetch metadata from TMDB
- Match episodes with TMDB data
- Generate organization plan

### Step 2: Review Results

After dry-run completes:
- View all detected shows with confidence levels
- See TMDB metadata (year, genre, poster)
- Check category classifications (国产剧, 日番, etc.)
- Review episode mappings (original → new paths)
- Select/deselect shows, seasons, or individual episodes

### Step 3: Execute Organization

1. Click "Execute Selected"
2. Monitor real-time progress
3. View completion statistics

Only selected items will be organized. The system will:
- Create season directories
- Rename episodes following Emby/Plex conventions
- Move files to target locations
- Clean up empty folders

## Features

### ✅ Implemented

- **Dry-Run Mode**: Preview organization without moving files
- **Job Management**: Track multiple organization jobs
- **Selection Control**: Choose exactly what to organize
- **Real-time Updates**: WebSocket-based progress tracking
- **Configuration UI**: Edit settings via web interface
- **Category Organization**: Automatic classification (国产剧, 日番, 欧美剧, etc.)
- **Statistics Dashboard**: View show counts and episode totals
- **Error Handling**: Graceful failure with error messages

### 🚧 Coming Soon

- Manual TMDB matching (search and reassign)
- Episode-level selection toggles
- Custom category rules editor
- Batch operations (select all, deselect all by criteria)
- Export dry-run results to JSON
- Undo/rollback support

## Architecture

### Backend Structure

```
backend/app/
├── main.py                    # FastAPI app
├── api/routes/
│   ├── jobs.py                # Dry-run & execution
│   ├── config.py              # Configuration management
│   ├── tmdb.py                # TMDB search
│   └── websocket.py           # Real-time updates
├── core/
│   └── organizer_wrapper.py  # Wraps TVShowOrganizer
├── services/
│   ├── cache_service.py       # Redis/in-memory cache
│   └── job_service.py         # Job state management
├── models/
│   └── api_models.py          # Pydantic schemas
└── utils/
    └── deserializers.py       # TVShow reconstruction
```

### Frontend Structure

```
frontend/src/
├── pages/
│   ├── HomePage.tsx           # Start dry-run
│   ├── ReviewPage.tsx         # Review & select
│   ├── ExecutePage.tsx        # Progress monitoring
│   └── ConfigPage.tsx         # Settings
├── store/
│   ├── useJobStore.ts         # Job state (Zustand)
│   └── useSelectionStore.ts   # Selection state
├── services/
│   └── api.ts                 # API client (Axios)
└── types/
    └── index.ts               # TypeScript types
```

## API Endpoints

### Jobs
- `POST /api/jobs/dry-run` - Start dry-run
- `GET /api/jobs/{job_id}` - Get job result
- `POST /api/jobs/{job_id}/execute` - Execute organization
- `PUT /api/jobs/{job_id}/shows/{show_id}/select` - Update selection
- `DELETE /api/jobs/{job_id}` - Delete job

### Configuration
- `GET /api/config` - Get config.yaml
- `PUT /api/config` - Update config.yaml
- `GET /api/config/categories` - Get category rules

### TMDB
- `POST /api/tmdb/search` - Search TV shows
- `GET /api/tmdb/show/{tmdb_id}` - Get show details

### WebSocket
- `WS /api/ws/{job_id}` - Real-time progress

## Configuration Options

### LLM Settings

- `api_key`: OpenAI or compatible API key
- `base_url`: Custom API endpoint (optional)
- `model`: Model name (gpt-4o-mini, gpt-4, gemini-2.5-flash, etc.)
- `batch_size`: How many folders to process at once (50)
- `rate_limit`: Requests per second (2)

### TMDB Settings

- `api_key`: TMDB API key
- `languages`: Preferred language codes
- `rate_limit`: Requests per second (40)

### Proxy Settings (Optional)

- `host`: Proxy hostname
- `port`: Proxy port

### Category Settings (Optional)

- `enabled`: Enable category-based organization
- `path`: Custom category.yaml path

## Caching

### Development Mode (Default)

Uses in-memory dictionary with thread-safe locks. No external dependencies required.

### Production Mode

Set `REDIS_URL` environment variable:

```bash
export REDIS_URL=redis://localhost:6379
```

Benefits:
- Persistence across restarts
- Better performance for concurrent users
- TTL-based auto-cleanup

## Troubleshooting

### Backend won't start

- Check Python version (3.7+)
- Install dependencies: `pip install -r backend/requirements.txt`
- Verify config.yaml exists with valid API keys

### Frontend won't start

- Check Node.js version (16+)
- Install dependencies: `npm install`
- Clear node_modules and reinstall if needed

### Dry-run fails

- Verify input directory exists and contains TV show folders
- Check LLM API key is valid
- Check TMDB API key is valid
- Look at backend logs for specific errors

### No shows detected

- Ensure input directory has subdirectories (one per show)
- Check folder names contain recognizable show names
- Try folders with clearer naming patterns

## Performance Tuning

### For Large Libraries (1000+ shows)

1. **Increase batch size** in config.yaml:
   ```yaml
   llm:
     batch_size: 100
   ```

2. **Use Redis** for caching:
   ```bash
   export REDIS_URL=redis://localhost:6379
   ```

3. **Adjust rate limits** if you have higher API quotas:
   ```yaml
   llm:
     rate_limit: 5
   tmdb:
     rate_limit: 50
   ```

## Production Deployment

### Backend (Docker Recommended)

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
COPY *.py *.yaml .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (Static Hosting)

```bash
cd frontend
npm run build
# Deploy dist/ folder to CDN or static hosting
```

### Environment Variables

```bash
# Backend
export REDIS_URL=redis://redis:6379
export OPENAI_API_KEY=sk-...
export TMDB_API_KEY=...

# Frontend (build time)
export VITE_API_BACKEND_URL=https://api.yourserver.com
```

## Security Considerations

1. **API Keys**: Never commit keys to git. Use environment variables.
2. **CORS**: Update allowed origins in `backend/app/main.py` for production.
3. **Rate Limiting**: Implement rate limiting for public-facing deployments.
4. **Input Validation**: All user inputs are validated server-side.

## Support & Contributing

- **Issues**: Report bugs at https://github.com/anthropics/aigua-tv/issues
- **Docs**: Full documentation at https://docs.aigua.tv
- **Discord**: Join our community for help

## License

MIT License - see LICENSE file for details

---

**Built with ❤️ using FastAPI, React, and Claude Code**
