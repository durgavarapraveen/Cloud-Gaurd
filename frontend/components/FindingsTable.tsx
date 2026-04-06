"use client";

import { useState } from "react";
import { Finding, Severity } from "@/lib/api";
import SeverityBadge from "./SeverityBadge";

const SEV_ORDER: Record<string, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
  INFO: 4,
};

export default function FindingsTable({
  findings,
  showPassed = false,
}: {
  findings: Finding[];
  showPassed?: boolean;
}) {
  const [selected, setSelected] = useState<Finding | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [filterService, setFilterService] = useState<string>("ALL");
  const [filterStatus, setFilterStatus] = useState<string>("FAIL");

  const services = Array.from(new Set(findings.map((f) => f.service))).sort();
  const severities: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];

  const visible = findings
    .filter((f) => filterStatus === "ALL" || f.status === filterStatus)
    .filter((f) => filterSeverity === "ALL" || f.severity === filterSeverity)
    .filter((f) => filterService === "ALL" || f.service === filterService)
    .sort(
      (a, b) => (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9),
    );

  const statusColour = (s: string) =>
    s === "PASS"
      ? "text-emerald-400"
      : s === "FAIL"
        ? "text-red-400"
        : s === "ERROR"
          ? "text-yellow-400"
          : "text-slate-500";

  return (
    <div className="flex gap-4 h-full">
      {/* Table */}
      <div className="flex-1 min-w-0">
        {/* Filters */}
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          {/* Status */}
          {["FAIL", "PASS", "ERROR", "ALL"].map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-3 py-1 rounded text-[11px] font-mono border transition-all
                ${
                  filterStatus === s
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                    : "border-white/[0.06] text-slate-500 hover:text-slate-300"
                }`}
            >
              {s}
            </button>
          ))}

          <div className="w-px h-4 bg-white/[0.06]" />

          {/* Severity */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 text-[11px] rounded px-2 py-1 font-mono outline-none"
          >
            <option value="ALL">All severities</option>
            {severities.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          {/* Service */}
          <select
            value={filterService}
            onChange={(e) => setFilterService(e.target.value)}
            className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 text-[11px] rounded px-2 py-1 font-mono outline-none"
          >
            <option value="ALL">All services</option>
            {services.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <div className="ml-auto text-[11px] text-slate-600 font-mono">
            {visible.length} findings
          </div>
        </div>

        {/* Table */}
        <div className="border border-white/[0.06] rounded-xl overflow-hidden">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                  Status
                </th>
                <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                  Severity
                </th>
                <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                  Rule
                </th>
                <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                  Resource
                </th>
                <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                  Service
                </th>
                <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                  Region
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {visible.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="text-center py-10 text-slate-600 text-[12px]"
                  >
                    No findings match the current filters.
                  </td>
                </tr>
              )}
              {visible.map((f, i) => (
                <tr
                  key={`${f.rule_id}-${f.resource_id}-${i}`}
                  onClick={() =>
                    setSelected(
                      f.rule_id === selected?.rule_id &&
                        f.resource_id === selected?.resource_id
                        ? null
                        : f,
                    )
                  }
                  className={`cursor-pointer transition-colors
                    ${
                      selected?.rule_id === f.rule_id &&
                      selected?.resource_id === f.resource_id
                        ? "bg-emerald-500/[0.06]"
                        : "hover:bg-white/[0.02]"
                    }`}
                >
                  <td
                    className={`px-4 py-2.5 font-mono font-medium ${statusColour(f.status)}`}
                  >
                    {f.status}
                  </td>
                  <td className="px-4 py-2.5">
                    <SeverityBadge severity={f.severity} size="xs" />
                  </td>
                  <td
                    className="px-4 py-2.5 font-mono text-slate-300 max-w-[180px] truncate"
                    title={f.rule_id}
                  >
                    {f.rule_id}
                  </td>
                  <td
                    className="px-4 py-2.5 text-slate-400 max-w-[200px] truncate font-mono text-[11px]"
                    title={f.resource_id}
                  >
                    {f.resource_name ? `${f.resource_name}` : f.resource_id}
                  </td>
                  <td className="px-4 py-2.5 text-slate-500 uppercase text-[10px] tracking-wider font-mono">
                    {f.service}
                  </td>
                  <td className="px-4 py-2.5 text-slate-500 text-[11px] font-mono">
                    {f.region}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail drawer */}
      {selected && (
        <div className="w-80 flex-shrink-0 bg-[#0d0d14] border border-white/[0.06] rounded-xl p-5 space-y-4 text-[12px] self-start">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="font-mono text-[11px] text-slate-500 mb-1">
                {selected.rule_id}
              </div>
              <div className="text-slate-200 text-[13px] leading-snug">
                {selected.rule_title}
              </div>
            </div>
            <button
              onClick={() => setSelected(null)}
              className="text-slate-600 hover:text-slate-300 flex-shrink-0 mt-0.5"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path
                  d="M2 2L12 12M12 2L2 12"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>

          <div className="h-px bg-white/[0.06]" />

          <div className="space-y-3">
            <Row
              label="Status"
              value={
                <span
                  className={`font-mono font-medium ${statusColour(selected.status)}`}
                >
                  {selected.status}
                </span>
              }
            />
            <Row
              label="Severity"
              value={<SeverityBadge severity={selected.severity} size="xs" />}
            />
            <Row
              label="Resource"
              value={
                <span className="font-mono text-[11px] text-slate-400 break-all">
                  {selected.resource_id}
                </span>
              }
            />
            <Row
              label="Type"
              value={
                <span className="text-slate-400">{selected.resource_type}</span>
              }
            />
            <Row
              label="Region"
              value={
                <span className="font-mono text-slate-400">
                  {selected.region}
                </span>
              }
            />
            <Row
              label="Check"
              value={
                <span className="font-mono text-[10px] text-slate-500 break-all">
                  {selected.operator} → {selected.actual_value ?? "null"}
                </span>
              }
            />
          </div>

          {selected.remediation && (
            <>
              <div className="h-px bg-white/[0.06]" />
              <div>
                <div className="text-[10px] text-slate-600 uppercase tracking-widest mb-2">
                  Remediation
                </div>
                <div className="text-slate-400 leading-relaxed text-[11px]">
                  {selected.remediation}
                </div>
              </div>
            </>
          )}

          {selected.source_file && (
            <div className="text-[10px] text-slate-700 font-mono pt-1">
              {selected.source_file}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <div className="text-[10px] text-slate-600 uppercase tracking-wider w-16 flex-shrink-0 pt-0.5">
        {label}
      </div>
      <div className="flex-1">{value}</div>
    </div>
  );
}
