import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 10000,
});

/** Browser's own IANA timezone, e.g. "Africa/Nairobi". */
function getBrowserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return null; // Extremely old browsers only — safe to omit the signal.
  }
}

/**
 * Analyze an IP, plus the browser's own timezone for mismatch detection.
 * Pass an empty value for `ip` to analyze your own public IP.
 *
 * Returns { result, blocked }.
 * A 429 is not treated as a failure: the backend attaches the full
 * risk data in `detail`, so the UI can render a "blocked" state.
 * Any other failure throws an Error with a readable message.
 */
export async function analyzeIp(ip) {
  const body = {
    ...(ip ? { ip } : {}),
    browser_timezone: getBrowserTimezone(),
  };

  try {
    const { data } = await api.post("/analyze", body);
    return { result: data, blocked: false };
  } catch (err) {
    if (err.response?.status === 429) {
      return { result: err.response.data.detail, blocked: true };
    }

    if (err.response) {
      const detail = err.response.data?.detail;
      throw new Error(
        typeof detail === "string"
          ? detail
          : "The request was rejected. Check the IP address format."
      );
    }

    if (err.code === "ECONNABORTED") {
      throw new Error("The request timed out. Please try again.");
    }
    throw new Error("Cannot reach the API. Is the backend running on port 8000?");
  }
}