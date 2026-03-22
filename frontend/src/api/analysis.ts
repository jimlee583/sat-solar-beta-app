import type { AnalysisRequest, AnalysisResponse } from "../types/analysis";

export async function runAnalysis(
  req: AnalysisRequest
): Promise<AnalysisResponse> {
  const res = await fetch("/api/analyze/v3", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Analysis failed (${res.status}): ${detail}`);
  }
  return res.json();
}
