import type { AnalysisRequest, AnalysisResponse } from "../types/analysis";
import { apiFetch } from "./client";

export async function runAnalysis(
  req: AnalysisRequest,
): Promise<AnalysisResponse> {
  const res = await apiFetch("/api/analyze/v3", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return res.json() as Promise<AnalysisResponse>;
}
