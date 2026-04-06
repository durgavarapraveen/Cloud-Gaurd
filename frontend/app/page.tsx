"use client";

import { useState } from "react";
import { awsApi, ScanResult } from "@/lib/api";
import ScoreGauge from "@/components/Scoregauge";
import MetricCard from "@/components/MetricCard";
import SeverityBar from "@/components/SeverityBadge";
import FindingsTable from "@/components/FindingsTable";

export default function DashboardPage() {
  const [data, setData] = useState<ScanResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"overview" | "findings">("overview");

  async function runScan() {
    setScanning(true);
    setError(null);
    try {
      const result = await awsApi.scan();
      console.log("Scan result:", result);
      setData(result);
      setTab("overview");
    } catch (e: any) {
      setError(e.message ?? "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  const s = data?.summary;

  return (
    <div className="p-8 space-y-8 relative z-10">
      {/* Page header */}
      <div className="fade-up flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">
            Security Posture
          </h1>
          <p className="text-[13px] text-slate-500 mt-1">
            AWS account scan —{" "}
            {data?.scan_metadata?.account_id ?? "not scanned yet"}
          </p>
        </div>

        <button
          onClick={runScan}
          disabled={scanning}
          className={`flex items-center gap-2.5 px-5 py-2.5 rounded-lg text-[13px] font-medium transition-all border
            ${
              scanning
                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-500/50 cursor-not-allowed"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500/50 active:scale-95"
            }`}
        >
          {scanning ? (
            <>
              <span className="w-3 h-3 rounded-full border-2 border-emerald-500/30 border-t-emerald-400 animate-spin" />
              Scanning…
            </>
          ) : (
            <>
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <circle
                  cx="6.5"
                  cy="6.5"
                  r="5.5"
                  stroke="currentColor"
                  strokeWidth="1.2"
                />
                <path
                  d="M4.5 6.5L6 8L8.5 5"
                  stroke="currentColor"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Run Scan
            </>
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="fade-up border border-red-500/30 bg-red-500/10 rounded-xl p-4 text-[13px] text-red-400">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!data && !scanning && (
        <div className="fade-up flex flex-col items-center justify-center py-24 text-center space-y-4 border border-dashed border-white/[0.08] rounded-2xl">
          <div className="w-12 h-12 rounded-full bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <circle
                cx="11"
                cy="11"
                r="9"
                stroke="#334155"
                strokeWidth="1.5"
              />
              <path
                d="M7 11L10 14L15 8"
                stroke="#334155"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <div className="text-slate-400 text-[14px]">No scan data</div>
            <div className="text-slate-600 text-[12px] mt-1">
              Click Run Scan to fetch your AWS security posture
            </div>
          </div>
        </div>
      )}

      {/* Scanning skeleton */}
      {scanning && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="bg-[#0d0d14] border border-white/[0.06] rounded-xl p-5 h-24 animate-pulse"
              />
            ))}
          </div>
          <div className="bg-[#0d0d14] border border-white/[0.06] rounded-xl h-40 animate-pulse" />
        </div>
      )}

      {/* Results */}
      {data && s && !scanning && (
        <div className="space-y-6">
          {/* Tabs */}
          <div className="fade-up flex gap-1 border-b border-white/[0.06]">
            {(["overview", "findings"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-[12px] font-medium capitalize border-b-2 -mb-px transition-colors
                  ${
                    tab === t
                      ? "border-emerald-400 text-emerald-400"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
              >
                {t}
                {t === "findings" && (
                  <span className="ml-2 text-[10px] bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded font-mono">
                    {s.failed}
                  </span>
                )}
              </button>
            ))}
          </div>

          {tab === "overview" && (
            <div className="space-y-6">
              {/* Score + metrics */}
              <div className="fade-up fade-up-delay-1 grid grid-cols-5 gap-4">
                {/* Score gauge */}
                <div className="col-span-1 bg-[#0d0d14] border border-white/[0.06] rounded-xl p-6 flex items-center justify-center">
                  <ScoreGauge score={s.score} />
                </div>

                {/* Metrics */}
                <div className="col-span-4 grid grid-cols-4 gap-4">
                  <MetricCard
                    label="Total checks"
                    value={s.total}
                    sub="rules evaluated"
                  />
                  <MetricCard
                    label="Passed"
                    value={s.passed}
                    sub={`${s.total > 0 ? ((s.passed / s.total) * 100).toFixed(0) : 0}% of checks`}
                    accent="green"
                  />
                  <MetricCard
                    label="Failed"
                    value={s.failed}
                    sub="need remediation"
                    accent="red"
                  />
                  <MetricCard
                    label="Critical"
                    value={s.by_severity?.CRITICAL ?? 0}
                    sub="immediate action"
                    accent="red"
                  />
                </div>
              </div>

              {/* Severity breakdown + Service breakdown */}
              <div className="fade-up fade-up-delay-2 grid grid-cols-2 gap-4">
                {/* Severity */}
                <div className="bg-[#0d0d14] border border-white/[0.06] rounded-xl p-5">
                  <div className="text-[11px] text-slate-500 uppercase tracking-widest mb-4">
                    Failed by severity
                  </div>
                  <SeverityBar bySeverity={s.by_severity ?? {}} />
                </div>

                {/* Service */}
                <div className="bg-[#0d0d14] border border-white/[0.06] rounded-xl p-5">
                  <div className="text-[11px] text-slate-500 uppercase tracking-widest mb-4">
                    Checks by service
                  </div>
                  <div className="space-y-2.5">
                    {Object.entries(s.by_service ?? {}).map(([svc, count]) => {
                      const max = Math.max(
                        ...Object.values(s.by_service ?? {}),
                      );
                      return (
                        <div key={svc} className="flex items-center gap-3">
                          <div className="w-14 text-right text-[11px] font-mono text-slate-500 uppercase">
                            {svc}
                          </div>
                          <div className="flex-1 h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-slate-400 rounded-full transition-all duration-700"
                              style={{
                                width: `${max > 0 ? (count / max) * 100 : 0}%`,
                              }}
                            />
                          </div>
                          <div className="w-6 text-right text-[12px] font-mono text-slate-400">
                            {count}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Scan metadata */}
              {data.scan_metadata && (
                <div className="fade-up fade-up-delay-3 border border-white/[0.04] rounded-xl p-4 flex gap-8 text-[11px]">
                  <Meta label="Account" value={data.scan_metadata.account_id} />
                  <Meta
                    label="Regions"
                    value={data.scan_metadata.regions?.join(", ")}
                  />
                  <Meta
                    label="Scanned"
                    value={new Date(
                      data.scan_metadata.scanned_at,
                    ).toLocaleString()}
                  />
                  <Meta
                    label="Resources"
                    value={String(data.findings?.length ?? 0) + " findings"}
                  />
                </div>
              )}
            </div>
          )}

          {tab === "findings" && (
            <div className="fade-up">
              <FindingsTable findings={data.findings ?? []} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Meta({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <div className="text-slate-600 uppercase tracking-wider text-[10px] mb-1">
        {label}
      </div>
      <div className="text-slate-400 font-mono">{value ?? "—"}</div>
    </div>
  );
}
