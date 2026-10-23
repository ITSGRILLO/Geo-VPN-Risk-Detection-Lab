const LEVELS = {
  LOW: { label: "Low risk", className: "badge badge-low" },
  MEDIUM: { label: "Medium risk", className: "badge badge-medium" },
  HIGH: { label: "High risk", className: "badge badge-high" },
};

export default function RiskBadge({ level }) {
  const config = LEVELS[level] ?? LEVELS.LOW;
  // Text label carries the meaning; color is reinforcement only.
  return <span className={config.className}>{config.label}</span>;
}