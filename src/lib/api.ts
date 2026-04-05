import type { PipelineConfig } from "@/components/InputPanel";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface PipelineResult {
  nodes: number;
  edges: number;
  modulator_size: number;
  tds_size: number;
  img_modulator: string | null;
  img_tds: string | null;
  img_satellite: string | null;
}

export async function runPipeline(config: PipelineConfig): Promise<PipelineResult> {
  const body = {
    mode: config.mode,
    lat: config.lat,
    lon: config.lon,
    place: config.place,
    bbox_n: config.bbox.n,
    bbox_s: config.bbox.s,
    bbox_e: config.bbox.e,
    bbox_w: config.bbox.w,
    network_type: config.networkType,
    k_modulator: config.kModulator,
    max_nodes: config.maxNodes,
    radius: config.radius,
  };

  const res = await fetch(`${API_URL}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Pipeline request failed" }));
    throw new Error(err.detail || `Server error (${res.status})`);
  }

  return res.json();
}
