"use client";

import React, { useEffect, useState } from "react";
import { yamlApi } from "@/lib/api"; // You should create api functions to call /yaml endpoints
import YAML from "yaml";
import dynamic from "next/dynamic";

// Dynamically load AceEditor and its modes/themes only in the browser
const AceEditor = dynamic(
  async () => {
    const ace = await import("react-ace");

    // Import mode and theme dynamically (after window exists)
    await import("ace-builds/src-noconflict/mode-yaml");
    await import("ace-builds/src-noconflict/theme-monokai");

    return ace;
  },
  { ssr: false },
);

interface Policy {
  _id: string;
  provider: string;
  service: string;
  data: any;
}

const CLOUD_PROVIDERS = ["AWS", "Azure", "GCP"]; // Replace with your actual providers

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filterProvider, setFilterProvider] = useState<string | null>(null);
  const [filterService, setFilterService] = useState<string | null>(null);

  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [yamlContent, setYamlContent] = useState("");

  // Fetch policies
  const loadPolicies = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await yamlApi.getPolicies();
      setPolicies(res);
    } catch (e: any) {
      setError(e.message ?? "Failed to fetch policies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPolicies();
  }, []);

  const filteredPolicies = Array.isArray(policies)
    ? policies.filter((p) => {
        return (
          (!filterProvider || p.provider === filterProvider) &&
          (!filterService || p.service === filterService)
        );
      })
    : [];

  // Start creating a new policy
  const handleNew = () => {
    setEditingPolicy(null);
    setYamlContent("");
  };

  // Start editing a policy
  const handleEdit = (policy: Policy) => {
    setEditingPolicy(policy);
    setYamlContent(YAML.stringify(policy.data));
  };

  // Save policy
  const handleSave = async () => {
    try {
      //   if (editingPolicy) {
      //     await yamlApi.updatePolicy(editingPolicy._id, yamlContent);
      //   } else {
      await yamlApi.createPolicy(
        editingPolicy?.provider ?? "AWS",
        editingPolicy?.service ?? "s3",
        yamlContent,
      );
      //   }
      await loadPolicies();
      setEditingPolicy(null);
      setYamlContent("");
    } catch (e: any) {
      setError(e.message ?? "Failed to save policy");
    }
  };

  return (
    <div className="p-8 space-y-6 relative z-10">
      {/* Header */}
      <div className="flex items-center justify-between fade-up">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">
            Policies
          </h1>
          <p className="text-[13px] text-slate-500 mt-1">
            Manage YAML policies for your cloud providers
          </p>
        </div>

        <button
          onClick={handleNew}
          className="px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[12px] font-medium hover:bg-emerald-500/30"
        >
          New Policy
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap fade-up">
        <select
          value={filterProvider ?? ""}
          onChange={(e) => setFilterProvider(e.target.value || null)}
          className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 px-2 py-1 rounded text-[12px]"
        >
          <option value="">All Providers</option>
          {CLOUD_PROVIDERS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Filter by service"
          value={filterService ?? ""}
          onChange={(e) => setFilterService(e.target.value || null)}
          className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 px-2 py-1 rounded text-[12px]"
        />
      </div>

      {/* Policies list */}
      <div className="divide-y divide-white/[0.06] rounded-xl border border-white/[0.06] overflow-hidden fade-up">
        {filteredPolicies.length === 0 && (
          <div className="py-12 text-center text-[12px] text-slate-600">
            No policies found
          </div>
        )}

        {filteredPolicies.map((policy) => (
          <div
            key={policy._id}
            className="px-4 py-3 flex justify-between items-center hover:bg-white/[0.02] transition-colors cursor-pointer"
            onClick={() => handleEdit(policy)}
          >
            <div className="text-[12px] font-mono text-slate-300 truncate">
              {policy.provider} / {policy.service}
            </div>
            <button
              onClick={() => handleEdit(policy)}
              className="text-[10px] text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded hover:bg-emerald-500/10"
            >
              Edit
            </button>
          </div>
        ))}
      </div>

      {/* YAML editor modal */}
      {(editingPolicy !== null || yamlContent) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#0d0d14] p-6 rounded-xl w-11/12 max-w-3xl max-h-[80vh] overflow-auto space-y-4">
            <h2 className="text-white font-semibold text-lg">
              {editingPolicy ? "Edit Policy" : "New Policy"}
            </h2>

            <div className="flex gap-2 flex-wrap">
              <select
                value={editingPolicy?.provider ?? "AWS"}
                onChange={(e) =>
                  setEditingPolicy({
                    ...editingPolicy!,
                    provider: e.target.value,
                  } as Policy)
                }
                className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 px-2 py-1 rounded text-[12px]"
              >
                {CLOUD_PROVIDERS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>

              <input
                type="text"
                placeholder="Service"
                value={editingPolicy?.service ?? ""}
                onChange={(e) =>
                  setEditingPolicy({
                    ...editingPolicy!,
                    service: e.target.value,
                  } as Policy)
                }
                className="bg-[#0d0d14] border border-white/[0.06] text-slate-400 px-2 py-1 rounded text-[12px]"
              />
            </div>

            <AceEditor
              mode="yaml"
              theme="monokai"
              width="100%"
              height="400px"
              value={yamlContent}
              onChange={setYamlContent}
              setOptions={{
                fontSize: 12,
                showPrintMargin: false,
                highlightActiveLine: true,
                showGutter: true,
                tabSize: 2,
              }}
            />

            {error && <div className="text-red-400 text-[12px]">{error}</div>}

            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => {
                  setEditingPolicy(null);
                  setYamlContent("");
                }}
                className="px-4 py-2 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
