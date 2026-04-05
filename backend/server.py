"""
FastAPI server wrapping the TDS Pipeline.

Deploy this alongside your pipeline code (tds_pipeline.py, block_graph_deletion.py,
and the mintds_opt_new executable).

Install: pip install fastapi uvicorn
Run:     uvicorn server:app --host 0.0.0.0 --port 8000
"""

import base64
import os
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

# Import your pipeline
from tds_pipeline import PipelineArgs, run_pipeline_for_ui

app = FastAPI(title="TDS Pipeline API", version="1.0.0")

# Allow all origins in dev — lock this down for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PipelineRequest(BaseModel):
    mode: str = "point"
    lat: Optional[float] = None
    lon: Optional[float] = None
    place: Optional[str] = None
    bbox_n: Optional[float] = None
    bbox_s: Optional[float] = None
    bbox_e: Optional[float] = None
    bbox_w: Optional[float] = None
    network_type: str = "drive"
    k_modulator: int = Field(default=10, ge=1, le=20)
    max_nodes: int = Field(default=100, ge=10, le=1000)
    radius: int = Field(default=200, ge=50, le=2000)


class PipelineResponse(BaseModel):
    nodes: int
    edges: int
    modulator_size: int
    tds_size: int
    img_modulator: Optional[str] = None   # base64 PNG
    img_tds: Optional[str] = None         # base64 PNG
    img_satellite: Optional[str] = None   # base64 PNG


def _read_image_b64(path: Optional[str]) -> Optional[str]:
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return None


@app.post("/api/run", response_model=PipelineResponse)
async def run_pipeline(req: PipelineRequest):
    point = [req.lat, req.lon] if req.mode == "point" and req.lat and req.lon else None
    place = req.place if req.mode == "place" else None
    bbox = (
        [req.bbox_n, req.bbox_s, req.bbox_e, req.bbox_w]
        if req.mode == "bbox" and all(v is not None for v in [req.bbox_n, req.bbox_s, req.bbox_e, req.bbox_w])
        else None
    )

    args = PipelineArgs(
        point=point,
        place=place,
        bbox=bbox,
        radius=req.radius,
        k=req.k_modulator,
        maxnodes=req.max_nodes,
        network=req.network_type,
    )

    try:
        results = run_pipeline_for_ui(args)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Pipeline execution failed")

    return PipelineResponse(
        nodes=results.get("nodes", 0),
        edges=results.get("edges", 0),
        modulator_size=results.get("modulator_size", 0),
        tds_size=results.get("tds_size", 0),
        img_modulator=_read_image_b64(results.get("img_modulator")),
        img_tds=_read_image_b64(results.get("img_tds")),
        img_satellite=_read_image_b64(results.get("img_satellite")),
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
