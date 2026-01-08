# aigua.tv WebUI Frontend

React + TypeScript frontend for the aigua.tv TV show organizer.

## Features

- **Dry-Run Preview**: See organization plan before moving files
- **Interactive Review**: Select/deselect shows, seasons, and episodes
- **Real-time Progress**: Live updates during execution
- **Manual TMDB Matching**: Search and correct show matches (coming soon)
- **Configuration Editor**: Edit settings via UI

## Tech Stack

- React 18 + TypeScript
- Material-UI (MUI) for components
- Zustand for state management
- Axios for API communication
- React Router for navigation
- Vite for build tooling

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

The frontend will run at http://localhost:5173

The Vite dev server automatically proxies `/api` requests to the backend at `http://localhost:8000`.

## Building for Production

```bash
npm run build
```

Build output goes to `dist/` directory.

## Project Structure

```
src/
├── main.tsx              # Entry point
├── App.tsx               # Root component with routing
├── pages/                # Page components
│   ├── HomePage.tsx      # Start dry-run
│   ├── ReviewPage.tsx    # Review results
│   ├── ExecutePage.tsx   # Execution progress
│   └── ConfigPage.tsx    # Configuration editor
├── store/                # Zustand stores
│   ├── useJobStore.ts    # Job state management
│   └── useSelectionStore.ts  # Selection state
├── services/
│   └── api.ts            # API client
└── types/
    └── index.ts          # TypeScript types
```

## Usage

1. **Start Dry-Run**:
   - Enter input and output directories
   - Click "Start Dry-Run"
   - Wait for processing

2. **Review Results**:
   - View detected shows with metadata
   - Select/deselect shows, seasons, episodes
   - Check episode counts and paths

3. **Execute**:
   - Click "Execute Selected"
   - Monitor real-time progress
   - View completion statistics

4. **Configure**:
   - Edit LLM and TMDB API keys
   - Adjust rate limits and settings
   - Save configuration

## Environment Variables

- `VITE_API_BACKEND_URL`: Backend URL (default: http://localhost:8000)

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Browser Support

Modern browsers supporting ES2020:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Contributing

The frontend is designed to be easily extensible:

- **Adding Pages**: Create in `src/pages/` and add route in `App.tsx`
- **Adding Components**: Create in `src/components/`
- **Adding State**: Create new Zustand store in `src/store/`
- **Adding API Calls**: Add to `src/services/api.ts`
