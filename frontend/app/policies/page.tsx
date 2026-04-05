"use client";

import React, { useState, useEffect, useMemo } from "react";
import { yamlApi, Rule } from "@/lib/api";
import SeverityBadge from "@/components/SeverityBadge";
import Link from "next/link";

// ── What the /yaml/policies/ endpoint actually returns ──────────
interface YamlPolicyResource {
  provider: string;
  service: string;
  data: {
    rules: Omit<Rule, "provider" | "service">[];
  };
  _id: string;
}

interface YamlPoliciesResponse {
  resources: YamlPolicyResource[];
}

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const [providerFilter, setProviderFilter] = useState<string>("ALL");
  const [serviceFilter, setServiceFilter] = useState<string>("ALL");

  async function loadPolicies() {
    setLoading(true);
    setError(null);
    try {
      const res = (await yamlApi.getPolicies({
        provider: null,
      })) as unknown as YamlPoliciesResponse;
      const allRules: Rule[] = res.resources.flatMap((r) =>
        r.data.rules.map((rule) => ({
          ...rule,
          provider: r.provider,
          service: r.service,
          _id: r._id,
        })),
      );
      console.log("Loaded policies:", allRules);
      setPolicies(allRules);
    } catch (err: any) {
      setError(err.message || "Failed to load policies");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPolicies();
  }, []);
  useEffect(() => {
    setServiceFilter("ALL");
  }, [providerFilter]);

  const grouped = useMemo(
    () =>
      policies.reduce<Record<string, Record<string, Rule[]>>>((acc, rule) => {
        const prov = rule.provider ?? "UNKNOWN";
        const svc = rule.service ?? "UNKNOWN";
        if (!acc[prov]) acc[prov] = {};
        if (!acc[prov][svc]) acc[prov][svc] = [];
        acc[prov][svc].push(rule);
        return acc;
      }, {}),
    [policies],
  );

  const allProviders = Object.keys(grouped);

  const availableServices = useMemo(() => {
    if (providerFilter === "ALL")
      return Array.from(new Set(policies.map((r) => r.service))).sort();
    return Object.keys(grouped[providerFilter] ?? {}).sort();
  }, [grouped, providerFilter, policies]);

  const visible = useMemo(
    () =>
      policies.filter(
        (r) =>
          (providerFilter === "ALL" || r.provider === providerFilter) &&
          (serviceFilter === "ALL" || r.service === serviceFilter),
      ),
    [policies, providerFilter, serviceFilter],
  );

  const visibleGrouped = useMemo(
    () =>
      visible.reduce<Record<string, Record<string, Rule[]>>>((acc, rule) => {
        const prov = rule.provider ?? "UNKNOWN";
        const svc = rule.service ?? "UNKNOWN";
        const _id = rule._id;
        if (!acc[prov]) acc[prov] = {};
        if (!acc[prov][svc]) acc[prov][svc] = [];
        acc[prov][svc].push(rule);
        return acc;
      }, {}),
    [visible],
  );

  const toggleExpand = (id: string) =>
    setExpanded((prev) => (prev === id ? null : id));

  const handleDeletePolicy = async (id: string) => {
    if (!confirm("Are you sure you want to delete this policy?")) return;
    try {
      await yamlApi.deletePolicy(id);
      await loadPolicies();
    } catch (e: any) {
      alert(e.message || "Failed to delete policy");
    }
  };

  return (
    <div className="p-8 space-y-6 relative z-10">
      <div className="flex items-start justify-between">
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
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-medium transition-all border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20
            `}
          >
            Create New Policy
          </Link>
          <button
            onClick={loadPolicies}
            disabled={loading}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-medium transition-all border
            ${
              loading
                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-500/50 cursor-not-allowed"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
            }`}
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="border border-red-500/30 bg-red-500/10 rounded-xl p-4 text-[13px] text-red-400">
          {error}
        </div>
      )}

      <div className="flex gap-3 flex-wrap items-center">
        <select
          value={providerFilter}
          onChange={(e) => setProviderFilter(e.target.value)}
          className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 text-[12px] rounded-lg px-3 py-2 font-mono outline-none"
        >
          <option value="ALL">All providers</option>
          {allProviders.map((p) => (
            <option key={p} value={p}>
              {p.toUpperCase()}
            </option>
          ))}
        </select>

        <select
          value={serviceFilter}
          onChange={(e) => setServiceFilter(e.target.value)}
          className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 text-[12px] rounded-lg px-3 py-2 font-mono outline-none"
        >
          <option value="ALL">All services</option>
          {availableServices.map((s) => (
            <option key={s} value={s}>
              {s.toUpperCase()}
            </option>
          ))}
        </select>

        {(providerFilter !== "ALL" || serviceFilter !== "ALL") && (
          <button
            onClick={() => {
              setProviderFilter("ALL");
              setServiceFilter("ALL");
            }}
            className="text-slate-500 text-[12px] hover:text-slate-300 transition-colors"
          >
            Clear filters
          </button>
        )}

        <div className="ml-auto text-[11px] text-slate-600 font-mono">
          {visible.length} / {policies.length} rules
        </div>
      </div>

      {loading && (
        <div className="border border-white/[0.06] rounded-xl overflow-hidden">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="h-10 border-b border-white/[0.04] bg-white/[0.01] animate-pulse"
            />
          ))}
        </div>
      )}

      {!loading && policies.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center py-24 border border-dashed border-white/[0.08] rounded-2xl text-center space-y-3">
          <div className="text-slate-500 text-[13px]">No policies found</div>
          <div className="text-slate-600 text-[12px]">
            Check that your YAML files are in the policies folder
          </div>
        </div>
      )}

      {!loading &&
        Object.keys(visibleGrouped).map((prov) => (
          <div key={prov} className="space-y-4">
            <h2 className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest pt-2">
              {prov}
            </h2>

            {Object.keys(visibleGrouped[prov]).map((svc) => {
              const rules = visibleGrouped[prov][svc];
              return (
                <div key={svc} className="space-y-1.5">
                  <h3 className="text-[10px] font-medium text-slate-600 uppercase tracking-wider px-1">
                    {svc} — {rules.length} rules
                  </h3>

                  <div className="border border-white/[0.06] rounded-xl overflow-hidden">
                    <table className="w-full text-[12px]">
                      <thead>
                        <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                          <th className="w-8 px-3 py-2.5" />
                          <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                            ID
                          </th>
                          <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                            Title
                          </th>
                          <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                            Severity
                          </th>
                          <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                            Operator
                          </th>
                          <th className="text-left px-4 py-2.5 text-[10px] text-slate-600 uppercase tracking-wider font-medium">
                            Actions
                          </th>
                        </tr>
                      </thead>

                      <tbody className="divide-y divide-white/[0.04]">
                        {rules.map((rule) => (
                          <React.Fragment key={rule.id}>
                            <tr
                              onClick={() => toggleExpand(rule.id)}
                              className="cursor-pointer hover:bg-white/[0.02] transition-colors"
                            >
                              <td className="px-3 py-2.5 text-slate-600">
                                <svg
                                  width="10"
                                  height="10"
                                  viewBox="0 0 10 10"
                                  fill="none"
                                  className={`transition-transform duration-150 ${expanded === rule.id ? "rotate-90" : ""}`}
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
                              <td className="px-4 py-2.5 font-mono text-slate-300 whitespace-nowrap">
                                {rule.id}
                              </td>
                              <td className="px-4 py-2.5 text-slate-400 max-w-xs truncate">
                                {rule.title}
                              </td>
                              <td className="px-4 py-2.5">
                                <SeverityBadge
                                  severity={rule.severity}
                                  size="xs"
                                />
                              </td>
                              <td className="px-4 py-2.5 font-mono text-[11px] text-slate-600">
                                {rule.check?.operator}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-[11px] text-slate-600">
                                {/* <button
                                  className="text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded hover:bg-emerald-500/10"
                                  onClick={() => handleEditPolicy(rule._id)}
                                >
                                  Edit
                                </button> */}
                                <Link
                                  href={`/policies/edit/${rule._id}`}
                                  className="text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded hover:bg-emerald-500/10"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  edit
                                </Link>
                                <button
                                  className="ml-2 text-red-400 border border-red-500/20 px-2 py-1 rounded hover:bg-red-500/10"
                                  onClick={() => handleDeletePolicy(rule._id)}
                                >
                                  Delete
                                </button>
                              </td>
                            </tr>

                            {expanded === rule.id && (
                              <tr className="bg-white/[0.015]">
                                <td colSpan={6} className="px-8 py-5">
                                  <div className="grid grid-cols-2 gap-6 text-[12px]">
                                    <div className="space-y-3">
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
                                      {rule.resource_type && (
                                        <div>
                                          <div className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
                                            Resource Type
                                          </div>
                                          <div className="text-slate-500 font-mono text-[11px]">
                                            {rule.resource_type}
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
                                      {rule._source_file && (
                                        <div className="text-[10px] text-slate-700 font-mono pt-1">
                                          {rule._source_file}
                                        </div>
                                      )}
                                    </div>
                                    <div className="space-y-3">
                                      <div>
                                        <div className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
                                          Check
                                        </div>
                                        <div className="font-mono text-[11px] text-slate-500 bg-white/[0.03] rounded-lg p-3 space-y-0.5">
                                          <div>
                                            path:{" "}
                                            <span className="text-slate-400">
                                              {rule.check?.path}
                                            </span>
                                          </div>
                                          <div>
                                            operator:{" "}
                                            <span className="text-slate-400">
                                              {rule.check?.operator}
                                            </span>
                                          </div>
                                          {rule.check?.value && (
                                            <div>
                                              value:{" "}
                                              <span className="text-slate-400">
                                                {rule.check.value}
                                              </span>
                                            </div>
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
        ))}
    </div>
  );
}
