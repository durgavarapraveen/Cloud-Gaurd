"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { yamlApi } from "@/lib/api";

// ── tiny yaml serialiser (no external dep needed for this shape) ──
// Converts the rules array back to the YAML string the backend expects.
// Uses js-yaml if available, falls back to JSON-based representation.
function rulesToYaml(rules: any[]): string {
  // Build a hand-crafted YAML string that matches your policy file format
  const lines: string[] = ["rules:"];
  for (const rule of rules) {
    lines.push(`  - id: "${rule.id}"`);
    lines.push(`    title: "${rule.title}"`);
    lines.push(`    severity: ${rule.severity}`);
    lines.push(`    service: ${rule.service}`);
    lines.push(`    resource_type: ${rule.resource_type}`);
    if (rule.description) {
      // multi-line description uses YAML block scalar
      lines.push(`    description: >`);
      lines.push(`      ${rule.description}`);
    }
    if (rule.check) {
      lines.push(`    check:`);
      lines.push(`      path: ${rule.check.path}`);
      lines.push(`      operator: ${rule.check.operator}`);
      if (rule.check.value !== undefined && rule.check.value !== null) {
        lines.push(`      value: "${rule.check.value}"`);
      }
    }
    if (rule.remediation) {
      lines.push(`    remediation: "${rule.remediation}"`);
    }
    if (rule.cis_reference) {
      lines.push(`    cis_reference: "${rule.cis_reference}"`);
    }
  }
  return lines.join("\n");
}

// ── Status pill ────────────────────────────────────────────────
type SaveStatus = "idle" | "saving" | "saved" | "error";

function StatusPill({
  status,
  error,
}: {
  status: SaveStatus;
  error: string | null;
}) {
  if (status === "idle") return null;
  if (status === "saving")
    return (
      <span className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
        <span className="w-2.5 h-2.5 rounded-full border-2 border-slate-500 border-t-slate-200 animate-spin" />
        Saving…
      </span>
    );
  if (status === "saved")
    return (
      <span className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-mono">
        <span className="w-2 h-2 rounded-full bg-emerald-400" />
        Saved
      </span>
    );
  if (status === "error")
    return (
      <span
        className="flex items-center gap-1.5 text-[11px] text-red-400 font-mono"
        title={error ?? ""}
      >
        <span className="w-2 h-2 rounded-full bg-red-400" />
        {error ?? "Save failed"}
      </span>
    );
  return null;
}

// ── Line numbers ───────────────────────────────────────────────
function LineNumbers({ count }: { count: number }) {
  return (
    <div
      aria-hidden
      className="select-none text-right pr-4 pt-4 pb-4 text-[13px] leading-[1.625rem] font-mono text-slate-600 border-r border-white/[0.06] min-w-[3rem]"
    >
      {Array.from({ length: count }, (_, i) => (
        <div key={i + 1}>{i + 1}</div>
      ))}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────
export default function EditPolicyPage() {
  const params = useParams();
  const router = useRouter();
  const id = typeof params.id === "string" ? params.id : "";

  // Raw document from MongoDB
  const [doc, setDoc] = useState<any | null>(null);
  // YAML string shown in the editor
  const [yaml, setYaml] = useState<string>("");
  // Original YAML — used to detect unsaved changes
  const [original, setOriginal] = useState<string>("");

  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  const isDirty = yaml !== original;

  // ── Load ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!id) return;
    async function load() {
      setLoading(true);
      setFetchError(null);
      try {
        const res = await yamlApi.getPolicyById(id);
        const policy = res.policy;
        setDoc(policy);

        // Convert stored rules array → YAML string for the editor
        const yamlStr = rulesToYaml(policy.data?.rules ?? []);
        setYaml(yamlStr);
        setOriginal(yamlStr);
      } catch (err: any) {
        setFetchError(err.message || "Failed to load policy");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  // ── Save ──────────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!id || !isDirty) return;
    setSaveStatus("saving");
    setSaveError(null);
    try {
      await yamlApi.updatePolicy(
        id,
        doc?.provider || "",
        doc?.service || "",
        yaml,
      );
      setOriginal(yaml);
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2500);
    } catch (err: any) {
      setSaveError(err.message || "Save failed");
      setSaveStatus("error");
    }
  }, [id, yaml, isDirty]);

  // Ctrl+S / Cmd+S shortcut
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleSave]);

  const lineCount = yaml.split("\n").length;

  // ── Render ────────────────────────────────────────────────────

  if (loading)
    return (
      <div className="p-8 space-y-4">
        <div className="h-6 w-48 bg-white/[0.04] rounded animate-pulse" />
        <div className="h-[600px] bg-white/[0.02] border border-white/[0.06] rounded-xl animate-pulse" />
      </div>
    );

  if (fetchError)
    return (
      <div className="p-8">
        <div className="border border-red-500/30 bg-red-500/10 rounded-xl p-5 text-[13px] text-red-400">
          {fetchError}
        </div>
      </div>
    );

  return (
    <div className="p-8 space-y-5 relative z-10">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <button
              onClick={() => router.back()}
              className="text-slate-600 hover:text-slate-300 transition-colors"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path
                  d="M10 3L5 8L10 13"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
            <h1 className="text-xl font-semibold text-white tracking-tight">
              Edit Policy
            </h1>
          </div>

          {/* Document metadata */}
          {doc && (
            <div className="flex items-center gap-3 ml-7">
              <MetaPill label="Provider" value={doc.provider} />
              <MetaPill label="Service" value={doc.service} />
              <MetaPill label="ID" value={doc._id} mono />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <StatusPill status={saveStatus} error={saveError} />

          {isDirty && (
            <span className="text-[11px] text-yellow-400/70 font-mono">
              unsaved changes
            </span>
          )}

          <button
            onClick={() => {
              setYaml(original);
              setSaveStatus("idle");
            }}
            disabled={!isDirty}
            className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all
              ${
                isDirty
                  ? "border-white/[0.08] text-slate-400 hover:text-slate-200 hover:border-white/[0.15]"
                  : "border-white/[0.04] text-slate-600 cursor-not-allowed"
              }`}
          >
            Reset
          </button>

          <button
            onClick={handleSave}
            disabled={!isDirty || saveStatus === "saving"}
            className={`px-4 py-1.5 rounded-lg text-[12px] font-medium border transition-all
              ${
                isDirty && saveStatus !== "saving"
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                  : "border-white/[0.04] bg-transparent text-slate-600 cursor-not-allowed"
              }`}
          >
            Save <span className="text-[10px] opacity-50 ml-1">⌘S</span>
          </button>
        </div>
      </div>

      {/* Hint bar */}
      <div className="flex items-center gap-4 px-4 py-2.5 rounded-lg bg-white/[0.02] border border-white/[0.05] text-[11px] text-slate-600 font-mono">
        <span>YAML editor</span>
        <span className="w-px h-3 bg-white/[0.08]" />
        <span>{lineCount} lines</span>
        <span className="w-px h-3 bg-white/[0.08]" />
        <span>
          Edit the <span className="text-slate-400">rules:</span> block below —
          keep the indentation
        </span>
        <span className="w-px h-3 bg-white/[0.08]" />
        <span className="text-slate-500">Ctrl+S to save</span>
      </div>

      {/* YAML Editor */}
      <div className="border border-white/[0.08] rounded-xl overflow-hidden bg-[#0a0a10]">
        {/* Editor toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06] bg-white/[0.02]">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/40" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/40" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/40" />
          </div>
          <span className="text-[11px] text-slate-600 font-mono">
            {doc ? `${doc.provider}/${doc.service}.yaml` : "policy.yaml"}
          </span>
          <div className="w-16" />
        </div>

        {/* Editor body — line numbers + textarea side by side */}
        <div
          className="flex overflow-auto"
          style={{ minHeight: "520px", maxHeight: "70vh" }}
        >
          <LineNumbers count={lineCount} />

          <textarea
            value={yaml}
            onChange={(e) => {
              setYaml(e.target.value);
              if (saveStatus === "saved" || saveStatus === "error")
                setSaveStatus("idle");
            }}
            spellCheck={false}
            className="flex-1 resize-none bg-transparent text-slate-300 font-mono text-[13px] leading-[1.625rem] p-4 outline-none caret-emerald-400 w-full"
            style={{
              // Match line height to the line numbers
              lineHeight: "1.625rem",
              tabSize: 2,
            }}
            onKeyDown={(e) => {
              // Tab inserts 2 spaces instead of moving focus
              if (e.key === "Tab") {
                e.preventDefault();
                const start = e.currentTarget.selectionStart;
                const end = e.currentTarget.selectionEnd;
                const next =
                  yaml.substring(0, start) + "  " + yaml.substring(end);
                setYaml(next);
                // Restore cursor after state update
                requestAnimationFrame(() => {
                  e.currentTarget.selectionStart = start + 2;
                  e.currentTarget.selectionEnd = start + 2;
                });
              }
            }}
          />
        </div>
      </div>

      {/* Rules preview — parsed count from the yaml */}
      <RulesPreview yaml={yaml} />
    </div>
  );
}

// ── Rules preview — counts rules in the yaml without parsing ───
function RulesPreview({ yaml }: { yaml: string }) {
  const ruleCount = (yaml.match(/^\s*- id:/gm) ?? []).length;
  if (ruleCount === 0) return null;

  return (
    <div className="flex items-center gap-3 text-[12px] text-slate-600 font-mono px-1">
      <span className="text-slate-500">
        {ruleCount} rule{ruleCount !== 1 ? "s" : ""} detected in editor
      </span>
    </div>
  );
}

// ── Small metadata pill ────────────────────────────────────────
function MetaPill({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center gap-1.5 text-[11px]">
      <span className="text-slate-600">{label}:</span>
      <span className={`text-slate-400 ${mono ? "font-mono" : ""}`}>
        {value}
      </span>
    </div>
  );
}
