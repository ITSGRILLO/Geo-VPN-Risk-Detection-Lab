export default function SignalRow({ label, value }) {
  return (
    <div className="signal-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}