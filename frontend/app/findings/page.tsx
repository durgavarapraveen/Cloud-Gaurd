"use client";

import { useState } from "react";
import { awsApi, Finding } from "@/lib/api";
import FindingsTable from "@/components/FindingsTable";

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await awsApi.scan();
      setFindings(res.findings ?? []);
      setLoaded(true);
    } catch (e: any) {
      setError(e.message ?? "Failed to load findings");
    } finally {
      setLoading(false);
    }
  }

  const failed = findings.filter((f) => f.status === "FAIL").length;
  const critical = findings.filter(
    (f) => f.status === "FAIL" && f.severity === "CRITICAL",
  ).length;

  return (
    <div className="p-8 space-y-6 relative z-10">
      {/* Header */}
      <div className="fade-up flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">
            Findings
          </h1>
          <p className="text-[13px] text-slate-500 mt-1">
            All compliance check results across your AWS resources
          </p>
        </div>

        <button
          onClick={load}
          disabled={loading}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-medium transition-all border
            ${
              loading
                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-500/50 cursor-not-allowed"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
            }`}
        >
          {loading ? (
            <>
              <span className="w-3 h-3 rounded-full border-2 border-emerald-500/30 border-t-emerald-400 animate-spin" />
              Loading…
            </>
          ) : (
            <>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path
                  d="M10 6A4 4 0 1 1 6 2"
                  stroke="currentColor"
                  strokeWidth="1.3"
                  strokeLinecap="round"
                />
                <path
                  d="M6 0L8 2L6 4"
                  stroke="currentColor"
                  strokeWidth="1.3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              {loaded ? "Refresh" : "Load findings"}
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="border border-red-500/30 bg-red-500/10 rounded-xl p-4 text-[13px] text-red-400">
          {error}
        </div>
      )}

      {/* Quick stats when loaded */}
      {loaded && (
        <div className="fade-up grid grid-cols-3 gap-4">
          <div className="bg-[#0d0d14] border border-white/[0.06] rounded-xl p-4 flex items-center gap-4">
            <div className="text-2xl font-bold font-mono text-white">
              {findings.length}
            </div>
            <div className="text-[11px] text-slate-500">total checks</div>
          </div>
          <div className="bg-[#0d0d14] border border-red-500/10 rounded-xl p-4 flex items-center gap-4">
            <div className="text-2xl font-bold font-mono text-red-400">
              {failed}
            </div>
            <div className="text-[11px] text-slate-500">failed checks</div>
          </div>
          <div className="bg-[#0d0d14] border border-red-500/10 rounded-xl p-4 flex items-center gap-4">
            <div className="text-2xl font-bold font-mono text-red-400">
              {critical}
            </div>
            <div className="text-[11px] text-slate-500">critical failures</div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loaded && !loading && (
        <div className="fade-up flex flex-col items-center justify-center py-24 border border-dashed border-white/[0.08] rounded-2xl text-center space-y-3">
          <div className="text-slate-500 text-[13px]">No findings loaded</div>
          <div className="text-slate-600 text-[12px]">
            Click &ldquo;Load findings&rdquo; to run a scan
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="border border-white/[0.06] rounded-xl overflow-hidden">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="h-10 border-b border-white/[0.04] bg-white/[0.01] animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Table */}
      {loaded && !loading && (
        <div className="fade-up">
          <FindingsTable findings={findings} />
        </div>
      )}
    </div>
  );
}
