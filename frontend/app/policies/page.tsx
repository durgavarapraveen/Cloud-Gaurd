"use client";

import React, { useState } from "react";
import {
  awsPoliciesApi,
  azurePoliciesApi,
  Rule,
  Severity,
  yamlApi,
} from "@/lib/api";
import SeverityBadge from "@/components/SeverityBadge";
import Link from "next/link";

const POLICY_SOURCES = [
  { key: "AWS", api: awsPoliciesApi },
  { key: "AZURE", api: azurePoliciesApi },
  // future sources: { key: "GCP", api: gcpPoliciesApi }
];

export default function PoliciesPage() {
  const [rulesBySource, setRulesBySource] = useState<Record<string, Rule[]>>(
    {},
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sevFilter, setSevFilter] = useState("ALL");
  const [svcFilter, setSvcFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showPopup, setShowPopup] = useState(false);

  // async function loadPolicies(sourceKey: string | "ALL") {
  //   setShowPopup(false);
  //   setLoading(true);
  //   setError(null);

  //   try {
  //     const newRulesBySource: Record<string, Rule[]> = {};

  //     const sourcesToLoad =
  //       sourceKey === "ALL"
  //         ? POLICY_SOURCES
  //         : POLICY_SOURCES.filter((s) => s.key === sourceKey);

  //     for (const source of sourcesToLoad) {
  //       const res = await source.api.all();
  //       newRulesBySource[source.key] = res.rules ?? [];
  //     }

  //     setRulesBySource(newRulesBySource);
  //   } catch (e: any) {
  //     setError(e.message ?? "Failed to load policies");
  //   } finally {
  //     setLoading(false);
  //   }
  // }

  async function loadPolicies(sourceKey: string | "ALL") {
    setShowPopup(false);
    setLoading(true);
    setError(null);

    try {
      const newRulesBySource: Record<string, Rule[]> = {};
      const details = { provider: sourceKey === "ALL" ? null : sourceKey };

      const policiesALL = await yamlApi.getPolicies(details);

      console.log("Fetched policies:", policiesALL);
    } catch (e: any) {
      setError(e.message ?? "Failed to load policies");
    } finally {
      setLoading(false);
    }
  }

  const severities: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];

  return (
    <div className="p-8 space-y-6 relative z-10">
      {/* Header */}
      <div className="fade-up flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">
            Policies
          </h1>
          <p className="text-[13px] text-slate-500 mt-1">
            YAML compliance rules loaded into the scanner
          </p>
        </div>

        <div className="flex row gap-2">
          <Link
            href="/policies/create"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-medium transition-all border
            ${
              loading
                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-500/50 cursor-not-allowed"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
            }`}
          >
            + Create custom policy
          </Link>

          <button
            onClick={() => setShowPopup(true)}
            disabled={loading}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-medium transition-all border
            ${
              loading
                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-500/50 cursor-not-allowed"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
            }`}
          >
            {loading
              ? "Loading…"
              : Object.keys(rulesBySource).length
                ? "Refresh"
                : "Load policies"}
          </button>
        </div>
      </div>

      {error && (
        <div className="border border-red-500/30 bg-red-500/10 rounded-xl p-4 text-[13px] text-red-400">
          {error}
        </div>
      )}

      {/* Source selection popup */}
      {showPopup && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-[#0d0d14] rounded-xl p-6 space-y-4 w-80">
            <h2 className="text-white text-sm font-semibold">
              Select Policy Source
            </h2>
            <div className="flex flex-col gap-3">
              {[...POLICY_SOURCES.map((s) => s.key), "ALL"].map((src) => (
                <button
                  key={src}
                  onClick={() => loadPolicies(src)}
                  className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-2 rounded-lg hover:bg-emerald-500/20 transition-colors"
                >
                  {src} Policies
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowPopup(false)}
              className="mt-2 text-slate-500 text-xs hover:text-slate-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Render rules per source */}
      {Object.entries(rulesBySource).map(([sourceKey, rules]) => {
        const services = Array.from(
          new Set(rules.map((r) => r.service)),
        ).sort();

        const visible = rules
          .filter((r) => sevFilter === "ALL" || r.severity === sevFilter)
          .filter((r) => svcFilter === "ALL" || r.service === svcFilter)
          .filter(
            (r) =>
              search === "" ||
              r.id.toLowerCase().includes(search.toLowerCase()) ||
              r.title.toLowerCase().includes(search.toLowerCase()),
          );

        return (
          <div key={sourceKey} className="fade-up space-y-4">
            <h2 className="text-sm font-semibold text-slate-400 uppercase">
              {sourceKey}
            </h2>

            {/* Filters + search */}
            <div className="flex items-center gap-3 flex-wrap">
              <input
                type="text"
                placeholder="Search rules…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-[#0d0d14] border border-white/[0.06] text-slate-300 placeholder-slate-600 text-[12px] font-mono rounded-lg px-3 py-2 w-56 outline-none focus:border-emerald-500/30"
              />

              <select
                value={sevFilter}
                onChange={(e) => setSevFilter(e.target.value)}
                className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 text-[11px] rounded-lg px-2 py-2 font-mono outline-none"
              >
                <option value="ALL">All severities</option>
                {severities.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>

              <select
                value={svcFilter}
                onChange={(e) => setSvcFilter(e.target.value)}
                className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 text-[11px] rounded-lg px-2 py-2 font-mono outline-none"
              >
                <option value="ALL">All services</option>
                {services.map((s) => (
                  <option key={s} value={s}>
                    {s.toUpperCase()}
                  </option>
                ))}
              </select>

              {(sevFilter !== "ALL" || svcFilter !== "ALL" || search) && (
                <button
                  onClick={() => {
                    setSevFilter("ALL");
                    setSvcFilter("ALL");
                    setSearch("");
                  }}
                  className="text-[11px] text-slate-600 hover:text-slate-400 transition-colors"
                >
                  Clear filters
                </button>
              )}

              <div className="ml-auto text-[11px] text-slate-600 font-mono">
                {visible.length} / {rules.length} rules
              </div>
            </div>

            {/* Table */}
            <div className="border border-white/[0.06] rounded-xl overflow-hidden">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                    <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium w-8" />
                    <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                      Rule ID
                    </th>
                    <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                      Title
                    </th>
                    <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                      Severity
                    </th>
                    <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                      Service
                    </th>
                    <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                      Operator
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
                        No rules match the current filters.
                      </td>
                    </tr>
                  )}

                  {visible.map((rule) => (
                    <React.Fragment key={rule.id}>
                      <tr
                        onClick={() =>
                          setExpanded(expanded === rule.id ? null : rule.id)
                        }
                        className="cursor-pointer hover:bg-white/[0.02] transition-colors"
                      >
                        <td className="px-4 py-2.5 text-slate-600">
                          <svg
                            width="10"
                            height="10"
                            viewBox="0 0 10 10"
                            fill="none"
                            className={`transition-transform ${
                              expanded === rule.id ? "rotate-90" : ""
                            }`}
                          >
                            <path
                              d="M3 2L7 5L3 8"
                              stroke="currentColor"
                              strokeWidth="1.2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </td>
                        <td className="px-4 py-2.5 font-mono text-slate-300">
                          {rule.id}
                        </td>
                        <td className="px-4 py-2.5 text-slate-400 max-w-xs truncate">
                          {rule.title}
                        </td>
                        <td className="px-4 py-2.5">
                          <SeverityBadge severity={rule.severity} size="xs" />
                        </td>
                        <td className="px-4 py-2.5 text-slate-500 uppercase text-[10px] font-mono tracking-wider">
                          {rule.service}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-[11px] text-slate-600">
                          {rule.check?.operator}
                        </td>
                      </tr>

                      {expanded === rule.id && (
                        <tr className="bg-white/[0.015]">
                          <td colSpan={6} className="px-8 py-4">
                            <div className="grid grid-cols-2 gap-6 text-[12px]">
                              <div className="space-y-2">
                                {rule.description && (
                                  <div>
                                    <div className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
                                      Description
                                    </div>
                                    <div className="text-slate-400 leading-relaxed">
                                      {rule.description}
                                    </div>
                                  </div>
                                )}
                                {rule.cis_reference && (
                                  <div>
                                    <div className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
                                      CIS Reference
                                    </div>
                                    <div className="text-slate-500 font-mono text-[11px]">
                                      {rule.cis_reference}
                                    </div>
                                  </div>
                                )}
                              </div>
                              <div className="space-y-2">
                                <div>
                                  <div className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
                                    Check
                                  </div>
                                  <div className="font-mono text-[11px] text-slate-500">
                                    path: {rule.check?.path}
                                    <br />
                                    operator: {rule.check?.operator}
                                    {rule.check?.value && (
                                      <>
                                        <br />
                                        value: {rule.check.value}
                                      </>
                                    )}
                                  </div>
                                </div>
                                {rule.remediation && (
                                  <div>
                                    <div className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
                                      Remediation
                                    </div>
                                    <div className="text-slate-400 leading-relaxed text-[11px]">
                                      {rule.remediation}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
