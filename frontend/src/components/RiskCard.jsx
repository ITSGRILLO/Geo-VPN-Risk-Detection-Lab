import RiskBadge from "./RiskBadge";
import SignalRow from "./SignalRow";

const BREAKDOWN_LABELS = {
  vpn_detected: "Hosting / VPN network",
  proxy_detected: "Proxy detected",
  datacenter_asn: "Datacenter ASN",
  timezone_mismatch: "Timezone mismatch",
  too_many_requests: "Too many requests",
};

const yesNo = (value) => (value ? "Yes" : "No");

export default function RiskCard({ data, blocked }) {
  const triggered = Object.entries(data.breakdown).filter(([, points]) => points > 0);

  return (
    <section className="card" aria-labelledby="result-heading">
      <h2 id="result-heading">Analysis result</h2>

      {blocked && (
        <p className="alert alert-error" role="alert">
          This client exceeded the rate limit and is temporarily blocked
          (HTTP 429). Wait about a minute before trying again.
        </p>
      )}

      <div className="score-block">
        <div>
          <p className="score-label">Risk score</p>
          <p className="score-value">{data.risk_score}</p>
        </div>
        <RiskBadge level={data.risk_level} />
      </div>

      <dl className="signals">
        <SignalRow label="IP address" value={data.ip} />
        <SignalRow label="Country" value={data.country} />
        <SignalRow label="City" value={data.city} />
        <SignalRow label="IP timezone" value={data.timezone} />
        <SignalRow label="Browser timezone" value={data.browser_timezone ?? "Not provided"} />
        <SignalRow label="ISP" value={data.isp} />
        <SignalRow label="ASN" value={data.asn} />
        <SignalRow label="VPN / hosting" value={yesNo(data.vpn)} />
        <SignalRow label="Proxy" value={yesNo(data.proxy)} />
        <SignalRow label="Requests in last minute" value={data.requests_per_minute} />
      </dl>

      <h3>Why this score</h3>
      {triggered.length === 0 ? (
        <p className="muted">No risk signals were triggered.</p>
      ) : (
        <ul className="breakdown">
          {triggered.map(([key, points]) => (
            <li key={key}>
              <span>{BREAKDOWN_LABELS[key] ?? key}</span>
              <span>+{points}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}