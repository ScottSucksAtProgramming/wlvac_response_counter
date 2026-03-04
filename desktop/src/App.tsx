import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { openPath } from "@tauri-apps/plugin-opener";
import "./App.css";

type Counts = {
  callsAssignedToUs: string;
  callsWeWentTo: string;
  callsMissed: string;
  callsLikelyHandledByOutsideAgency: string;
};

type RunSummaryResponse = {
  success: boolean;
  outputPath: string;
  stdout: string;
  stderr: string;
  counts: Counts;
};

type RequestPayload = {
  dispatchPath: string;
  esoPath: string;
  outputDir: string;
  excludeUnits: string;
  wlvacUnits: string;
};

const DEFAULT_EXCLUDE = "290,291";
const DEFAULT_WLVAC = "292,293,294";

function App() {
  const [dispatchPath, setDispatchPath] = useState("");
  const [esoPath, setEsoPath] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [excludeUnits, setExcludeUnits] = useState(DEFAULT_EXCLUDE);
  const [wlvacUnits, setWlvacUnits] = useState(DEFAULT_WLVAC);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState("Ready. Select files, then click Generate Summary.");
  const [error, setError] = useState("");
  const [result, setResult] = useState<RunSummaryResponse | null>(null);

  useEffect(() => {
    void (async () => {
      const dir = await invoke<string>("default_output_dir");
      if (dir && !outputDir) {
        setOutputDir(dir);
      }
    })();
  }, [outputDir]);

  const canRun = useMemo(() => {
    return Boolean(dispatchPath && esoPath && outputDir && !isRunning);
  }, [dispatchPath, esoPath, outputDir, isRunning]);

  async function browseDispatch() {
    setError("");
    try {
      const selected = await invoke<string | null>("pick_dispatch_file");
      if (selected) {
        setDispatchPath(selected);
        setStatus("Dispatch report selected.");
      }
    } catch (err) {
      const msg = typeof err === "string" ? err : "Could not open dispatch file picker.";
      setError(msg);
      setStatus("Dispatch browse failed.");
    }
  }

  async function browseEso() {
    setError("");
    try {
      const selected = await invoke<string | null>("pick_eso_file");
      if (selected) {
        setEsoPath(selected);
        setStatus("ESO/ePCR report selected.");
      }
    } catch (err) {
      const msg = typeof err === "string" ? err : "Could not open ESO file picker.";
      setError(msg);
      setStatus("ESO browse failed.");
    }
  }

  async function browseOutputDir() {
    setError("");
    try {
      const selected = await invoke<string | null>("pick_output_dir");
      if (selected) {
        setOutputDir(selected);
        setStatus("Output folder selected.");
      }
    } catch (err) {
      const msg = typeof err === "string" ? err : "Could not open output folder picker.";
      setError(msg);
      setStatus("Output folder browse failed.");
    }
  }

  async function openOutput() {
    if (!result?.outputPath) return;
    setError("");
    try {
      await openPath(result.outputPath);
      setStatus(`Opened output: ${result.outputPath}`);
    } catch (err) {
      const msg = typeof err === "string" ? err : "Failed to open output file.";
      setError(msg);
      setStatus("Could not open output file.");
    }
  }

  async function runSummary() {
    setIsRunning(true);
    setError("");
    setStatus("Generating summary...");
    try {
      const payload: RequestPayload = {
        dispatchPath,
        esoPath,
        outputDir,
        excludeUnits: excludeUnits.trim() || DEFAULT_EXCLUDE,
        wlvacUnits: wlvacUnits.trim() || DEFAULT_WLVAC,
      };
      const response = await invoke<RunSummaryResponse>("run_summary", { req: payload });
      setResult(response);
      setStatus(`Summary complete. Saved to ${response.outputPath}`);
    } catch (err) {
      const msg = typeof err === "string" ? err : "Failed to generate summary.";
      setError(msg);
      setStatus("Generation failed. Review the error below.");
      setResult(null);
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <h1>WLVAC Response Counts</h1>
        <p className="sub">
          1) Select dispatch report (.xls), 2) select ESO/ePCR report (.csv), 3) choose output folder, then Generate.
        </p>
      </header>

      <section className="panel">
        <div className="field-group">
          <label>Dispatch Report (.xls)</label>
          <p className="hint">Raw CAD export file with dispatch message rows.</p>
          <div className="row">
            <input value={dispatchPath} onChange={(e) => setDispatchPath(e.target.value)} placeholder="Select dispatch report..." />
            <button onClick={browseDispatch} type="button">Browse</button>
          </div>
        </div>

        <div className="field-group">
          <label>ESO/ePCR Responses Report (.csv)</label>
          <p className="hint">ESO export with Incident Number, Unit, and Scene Address 1.</p>
          <div className="row">
            <input value={esoPath} onChange={(e) => setEsoPath(e.target.value)} placeholder="Select ESO/ePCR report..." />
            <button onClick={browseEso} type="button">Browse</button>
          </div>
        </div>

        <div className="field-group">
          <label>Output Folder</label>
          <p className="hint">A timestamped file will be created: WLVACResponseCounts-YYMMDD-HHMMSS.txt</p>
          <div className="row">
            <input value={outputDir} onChange={(e) => setOutputDir(e.target.value)} placeholder="Select output folder..." />
            <button onClick={browseOutputDir} type="button">Browse</button>
          </div>
        </div>

        <button className="advanced-toggle" type="button" onClick={() => setAdvancedOpen((v) => !v)}>
          {advancedOpen ? "Hide" : "Show"} Advanced Settings
        </button>
        {advancedOpen && (
          <div className="advanced">
            <div className="advanced-item">
              <label>Exclude Units</label>
              <input value={excludeUnits} onChange={(e) => setExcludeUnits(e.target.value)} />
            </div>
            <div className="advanced-item">
              <label>WLVAC Units</label>
              <input value={wlvacUnits} onChange={(e) => setWlvacUnits(e.target.value)} />
            </div>
          </div>
        )}

        <div className="actions">
          <button className="primary" onClick={runSummary} disabled={!canRun} type="button">
            {isRunning ? "Generating..." : "Generate Summary"}
          </button>
          <button onClick={openOutput} disabled={!result?.outputPath} type="button">
            Open Output
          </button>
        </div>

        <p className="status">{status}</p>
        {error && <pre className="error">{error}</pre>}
      </section>

      <section className="results">
        <h2>Results</h2>
        <div className="tiles">
          <article>
            <span>Assigned</span>
            <strong>{result?.counts.callsAssignedToUs ?? "-"}</strong>
          </article>
          <article>
            <span>Went</span>
            <strong>{result?.counts.callsWeWentTo ?? "-"}</strong>
          </article>
          <article>
            <span>Missed</span>
            <strong>{result?.counts.callsMissed ?? "-"}</strong>
          </article>
          <article>
            <span>Outside</span>
            <strong>{result?.counts.callsLikelyHandledByOutsideAgency ?? "-"}</strong>
          </article>
        </div>
        {result?.outputPath && <p className="path">Saved: {result.outputPath}</p>}
      </section>
    </main>
  );
}

export default App;
