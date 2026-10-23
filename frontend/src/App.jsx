import { useState } from "react";
import { analyzeIp } from "./api/client";
import RiskCard from "./components/RiskCard";

export default function App() {
  const [ip, setIp] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);
  const [blocked, setBlocked] = useState(false);
  const [error, setError] = useState("");

  async function runAnalysis(event) {
    event?.preventDefault();
    setStatus("loading");
    setError("");

    try {
      const { result: data, blocked: isBlocked } = await analyzeIp(ip.trim());
      setResult(data);
      setBlocked(isBlocked);
      setStatus("success");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  return (
    <main className="container">
      <header>
        <h1>Geo & VPN Risk Detection Lab</h1>
        <p className="muted">
          See how an IP address becomes a risk score: geolocation, network
          type, proxy signals and request rate.
        </p>
      </header>

      <form className="card" onSubmit={runAnalysis}>
        <label htmlFor="ip-input">IP address to analyze</label>
        <input
          id="ip-input"
          type="text"
          value={ip}
          onChange={(e) => setIp(e.target.value)}
          placeholder="Leave empty to analyze your own IP"
          autoComplete="off"
          spellCheck="false"
          aria-describedby="ip-help"
        />
        <p id="ip-help" className="muted">
          Example: 3.5.140.2 is an AWS address and should be flagged as hosting.
        </p>
        <button type="submit" disabled={status === "loading"}>
          {status === "loading" ? "Analyzing..." : "Analyze"}
        </button>
      </form>

      <div aria-live="polite" aria-busy={status === "loading"}>
        {status === "idle" && (
          <p className="empty">
            No analysis yet. Submit an IP address, or leave the field empty to
            check your own.
          </p>
        )}

        {status === "loading" && <p className="muted">Looking up signals...</p>}

        {status === "error" && (
          <div className="alert alert-error" role="alert">
            <p>{error}</p>
            <button type="button" className="button-secondary" onClick={runAnalysis}>
              Retry
            </button>
          </div>
        )}

        {status === "success" && result && (
          <RiskCard data={result} blocked={blocked} />
        )}
      </div>
    </main>
  );
}