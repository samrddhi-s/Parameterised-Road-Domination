# TDS Pipeline Backend

## Setup

1. Copy your pipeline files into this folder:
   - `tds_pipeline.py`
   - `block_graph_deletion.py`
   - `mintds_opt_new` (or `mintds_opt_new.exe`)

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   uvicorn server:app --host 0.0.0.0 --port 8000
   ```

4. Set the `VITE_API_URL` in the React app to your deployed URL (e.g., `https://your-server.com`).

## API

### `POST /api/run`
Runs the full pipeline. Returns nodes, edges, modulator size, TDS size, and base64-encoded visualization images.

### `GET /api/health`
Health check endpoint.

## Deploy Options
- **Railway**: Push this folder, set start command to `uvicorn server:app --host 0.0.0.0 --port $PORT`
- **Render**: Create a Web Service pointing to this folder
- **VPS**: Run with `uvicorn` or behind `gunicorn`
