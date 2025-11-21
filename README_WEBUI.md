# TV Show Organizer Web UI

Web-based user interface for the TV Show Media Library Organizer.

## Features

- **Configuration Management**: Edit config.yaml settings through the web interface
- **Folder Selection**: Browse and select source and target folders
- **Dry Run Preview**: Preview organization changes before executing
- **Manual TMDB Matching**: Search and manually match shows with TMDB
- **Selective Processing**: Choose which shows to organize
- **Real-time Progress**: Monitor organization progress in real-time

## Installation

### Backend

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure `config.yaml` is properly configured with your API keys.

### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

## Running

### Development Mode

1. Start the FastAPI backend:
```bash
python -m webui.main
```

Or using uvicorn directly:
```bash
uvicorn webui.main:app --reload --host 0.0.0.0 --port 8000
```

2. In another terminal, start the React frontend:
```bash
cd frontend
npm run dev
```

3. Open your browser to `http://localhost:3000`

### Production Mode

1. Build the frontend:
```bash
cd frontend
npm run build
```

2. Start the FastAPI backend (it will serve the built frontend):
```bash
python -m webui.main
```

Or:
```bash
uvicorn webui.main:app --host 0.0.0.0 --port 8000
```

3. Open your browser to `http://localhost:8000`

## Usage

1. **Configure**: Go to the Configuration page and set up your LLM and TMDB API keys
2. **Setup**: On the Setup page, select your source and target folders
3. **Preview**: Click "Start Dry Run" to see a preview of the organization
4. **Review**: Review the matches, deselect unwanted shows, or manually search for TMDB matches
5. **Execute**: Click "Execute Organization" to perform the actual file organization

## API Endpoints

The web UI exposes a REST API at `/api`:

- `GET /api/config` - Get configuration
- `PUT /api/config` - Update configuration
- `POST /api/folders/scan` - Scan source folder
- `GET /api/folders/browse` - Browse directory
- `POST /api/tmdb/search` - Search TMDB
- `POST /api/organize/dry-run` - Start dry-run
- `POST /api/organize/execute` - Execute organization
- `GET /api/organize/status/{job_id}` - Get job status
- `GET /api/preview/{job_id}` - Get preview data

## Troubleshooting

- **CORS errors**: Make sure the frontend proxy is configured correctly in `vite.config.js`
- **API connection errors**: Verify the backend is running and accessible
- **Configuration errors**: Check that `config.yaml` exists and has valid API keys
- **File permission errors**: Ensure the application has read/write access to source and target folders

