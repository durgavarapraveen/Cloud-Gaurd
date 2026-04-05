export default function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "green" | "red" | "orange" | "default";
}) {
  const accentClass = {
    green: "text-emerald-400",
    red: "text-red-400",
    orange: "text-orange-400",
    default: "text-white",
  }[accent ?? "default"];

  return (
    <div className="bg-[#0d0d14] border border-white/[0.06] rounded-xl p-5 flex flex-col gap-2">
      <div className="text-[11px] text-slate-500 uppercase tracking-widest">
        {label}
      </div>
      <div
        className={`text-3xl font-bold font-mono tracking-tight ${accentClass}`}
      >
        {value}
      </div>
      {sub && <div className="text-[11px] text-slate-600">{sub}</div>}
    </div>
  );
}
