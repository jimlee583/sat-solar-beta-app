import { useState } from "react";
import InputPanel from "./components/InputPanel";
import SummaryCards from "./components/SummaryCards";
import PlotSection from "./components/PlotSection";
import { runAnalysis } from "./api/analysis";
import type { AnalysisRequest, AnalysisResponse } from "./types/analysis";

export default function App() {
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze(req: AnalysisRequest) {
    setLoading(true);
    setError(null);
    try {
      const data = await runAnalysis(req);
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>Satellite Solar Environment Analyzer</h1>
        <span style={styles.version}>v3.0 — Constrained Articulation Tracking</span>
      </header>

      <div style={styles.body}>
        <aside style={styles.sidebar}>
          <InputPanel onAnalyze={handleAnalyze} loading={loading} />
        </aside>

        <main style={styles.main}>
          {error && <div style={styles.error}>{error}</div>}

          {!result && !error && (
            <div style={styles.placeholder}>
              Enter orbit parameters and click <strong>Analyze</strong> to generate results.
            </div>
          )}

          {result && (
            <>
              <SummaryCards data={result} />
              <PlotSection data={result} />
            </>
          )}
        </main>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: "100vh",
    background: "#e9ecef",
    fontFamily: "Inter, system-ui, -apple-system, sans-serif",
  },
  header: {
    background: "#212529",
    color: "#fff",
    padding: "1rem 2rem",
    display: "flex",
    alignItems: "baseline",
    gap: "1rem",
    flexWrap: "wrap",
  },
  title: {
    margin: 0,
    fontSize: "1.3rem",
    fontWeight: 700,
  },
  version: {
    fontSize: "0.8rem",
    color: "#adb5bd",
  },
  body: {
    display: "flex",
    gap: "1.5rem",
    padding: "1.5rem 2rem",
    alignItems: "flex-start",
    flexWrap: "wrap",
  },
  sidebar: {
    flexShrink: 0,
    width: "300px",
  },
  main: {
    flex: 1,
    minWidth: "0",
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  error: {
    padding: "0.75rem 1rem",
    background: "#f8d7da",
    color: "#842029",
    borderRadius: "6px",
    border: "1px solid #f5c2c7",
    fontSize: "0.9rem",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  placeholder: {
    padding: "3rem",
    textAlign: "center",
    color: "#6c757d",
    fontSize: "1rem",
    background: "#fff",
    borderRadius: "8px",
    border: "1px solid #dee2e6",
  },
};
