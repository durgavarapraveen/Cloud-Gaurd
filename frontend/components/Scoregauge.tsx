"use client";

export default function ScoreGauge({ score }: { score: number }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  const dash = (pct / 100) * circ;

  const colour = pct >= 90 ? "#10b981" : pct >= 70 ? "#eab308" : "#ef4444";

  const label = pct >= 90 ? "SECURE" : pct >= 70 ? "REVIEW" : "AT RISK";

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className="relative w-36 h-36">
        <svg
          width="144"
          height="144"
          viewBox="0 0 144 144"
          className="-rotate-90"
        >
          {/* Track */}
          <circle
            cx="72"
            cy="72"
            r={r}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="10"
          />
          {/* Progress */}
          <circle
            cx="72"
            cy="72"
            r={r}
            fill="none"
            stroke={colour}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circ}`}
            style={{
              transition: "stroke-dasharray 0.8s ease, stroke 0.4s ease",
            }}
          />
        </svg>
        {/* Centre text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-3xl font-bold font-mono"
            style={{ color: colour }}
          >
            {pct.toFixed(0)}
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5">/ 100</span>
        </div>
      </div>
      <div
        className="text-[11px] font-mono tracking-[0.15em] px-3 py-1 rounded border"
        style={{
          color: colour,
          borderColor: colour + "40",
          background: colour + "10",
        }}
      >
        {label}
      </div>
    </div>
  );
}
