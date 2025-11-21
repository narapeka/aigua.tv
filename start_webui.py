#!/usr/bin/env python3
"""
Startup script for TV Show Organizer Web UI
"""

import uvicorn
import sys
import socket
import argparse
from pathlib import Path


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def find_free_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    raise RuntimeError(f"Could not find a free port in range {start_port}-{start_port + max_attempts - 1}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start TV Show Organizer Web UI")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--auto-port",
        action="store_true",
        help="Automatically find a free port if the specified port is in use"
    )
    args = parser.parse_args()
    
    # Add project root to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # Check if port is in use
    port = args.port
    if is_port_in_use(port):
        if args.auto_port:
            port = find_free_port(port)
            print(f"Port {args.port} is in use, using port {port} instead")
        else:
            print(f"ERROR: Port {port} is already in use!")
            print(f"\nOptions:")
            print(f"  1. Kill the process using port {port}:")
            print(f"     lsof -ti:{port} | xargs kill -9")
            print(f"  2. Use a different port:")
            print(f"     python start_webui.py --port 8001")
            print(f"  3. Auto-find a free port:")
            print(f"     python start_webui.py --auto-port")
            sys.exit(1)
    
    print("Starting TV Show Organizer Web UI...")
    print(f"Backend API: http://localhost:{port}")
    print(f"API Docs: http://localhost:{port}/docs")
    print("\nTo start the frontend in development mode:")
    print("  cd frontend && npm run dev")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "webui.main:app",
        host=args.host,
        port=port,
        reload=True
    )

