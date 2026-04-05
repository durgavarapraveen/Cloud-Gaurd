"use client";

import { useState } from "react";
import { awsScannerApi } from "@/lib/api";

const CLOUD_PROVIDERS = {
  AWS: ["s3", "ec2", "rds", "iam"],
  Azure: ["vm", "storage", "sql", "ad"],
  GCP: ["compute", "storage", "sql", "iam"],
};

export default function ResourcesPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [service, setService] = useState<string>("s3");
  const [selected, setSelected] = useState<any>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [selectedServices, setSelectedServices] = useState<
    Record<string, string[]>
  >({});

  async function load() {
    if (selectedProviders.length === 0) {
      setError("Please select at least one cloud provider and service.");
      return;
    }
    setLoading(true);
    setError(null);
    setSelected(null);
    try {
      // For simplicity, calling AWS API only if AWS is selected
      const res = selectedProviders.includes("AWS")
        ? await awsScannerApi.scan({
            services: selectedServices["AWS"] ?? ["ALL"],
          })
        : {};

      // TODO: Add similar API calls for Azure/GCP if selected

      setData(res);
      setModalOpen(false);
    } catch (e: any) {
      setError(e.message ?? "Failed to fetch resources");
    } finally {
      setLoading(false);
    }
  }

  const handleProviderToggle = (provider: string) => {
    if (selectedProviders.includes(provider)) {
      setSelectedProviders((prev) => prev.filter((p) => p !== provider));
      setSelectedServices((prev) => {
        const copy = { ...prev };
        delete copy[provider];
        return copy;
      });
    } else {
      setSelectedProviders((prev) => [...prev, provider]);
      setSelectedServices((prev) => ({ ...prev, [provider]: [] }));
    }
  };

  const handleServiceToggle = (provider: string, svc: string) => {
    setSelectedServices((prev) => {
      const current = prev[provider] ?? [];
      if (current.includes(svc)) {
        return { ...prev, [provider]: current.filter((s) => s !== svc) };
      } else {
        return { ...prev, [provider]: [...current, svc] };
      }
    });
  };

  const resources: any[] = data?.resources?.[service] ?? [];

  return (
    <div className="p-8 space-y-6 relative z-10">
      {/* Header */}
      <div className="fade-up flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">
            Resources
          </h1>
          <p className="text-[13px] text-slate-500 mt-1">
            Raw AWS resource configurations fetched from your account
          </p>
        </div>

        <button
          onClick={() => setModalOpen(true)}
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
              Fetching…
            </>
          ) : data ? (
            "Refresh"
          ) : (
            "Fetch resources"
          )}
        </button>
      </div>

      {/* Modern Provider & Service Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[#12121b] p-6 rounded-2xl w-96 max-h-[80vh] overflow-auto shadow-lg border border-white/[0.08] space-y-6">
            <h2 className="text-white text-xl font-semibold tracking-tight">
              Select Cloud Providers & Services
            </h2>

            <div className="space-y-4">
              {Object.keys(CLOUD_PROVIDERS).map((provider) => (
                <div key={provider}>
                  {/* Provider checkbox */}
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-white font-medium">{provider}</span>
                    <input
                      type="checkbox"
                      checked={selectedProviders.includes(provider)}
                      onChange={() => handleProviderToggle(provider)}
                      className="accent-emerald-400 w-5 h-5"
                    />
                  </label>

                  {/* Services for selected provider */}
                  {selectedProviders.includes(provider) && (
                    <div className="ml-5 mt-2 space-y-2">
                      {CLOUD_PROVIDERS[
                        provider as keyof typeof CLOUD_PROVIDERS
                      ].map((svc) => (
                        <label
                          key={svc}
                          className="flex items-center justify-between cursor-pointer px-2 py-1 rounded hover:bg-white/5 transition"
                        >
                          <span className="text-slate-300 text-sm">{svc}</span>
                          <input
                            type="checkbox"
                            checked={selectedServices[provider]?.includes(svc)}
                            onChange={() => handleServiceToggle(provider, svc)}
                            className="accent-emerald-400 w-4 h-4"
                          />
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Footer actions */}
            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-white/5 text-white/60 hover:bg-white/10 transition"
              >
                Cancel
              </button>
              <button
                onClick={load}
                className="px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition"
              >
                Fetch
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="border border-red-500/30 bg-red-500/10 rounded-xl p-4 text-[13px] text-red-400">
          {error}
        </div>
      )}

      {/* Summary strip */}
      {data?.summary && (
        <div className="fade-up flex items-center gap-3 flex-wrap">
          <div className="text-[12px] text-slate-500 font-mono">
            {data.summary.total_resources} total resources
          </div>
          <div className="w-px h-3 bg-white/[0.08]" />
          {Object.entries(data.summary.by_service ?? {}).map(
            ([svc, count]: any) => (
              <button
                key={svc}
                onClick={() => {
                  setService(svc);
                  setSelected(null);
                }}
                className={`text-[11px] font-mono px-2.5 py-1 rounded border transition-all uppercase
                ${
                  service === svc
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                    : "border-white/[0.06] text-slate-500 hover:text-slate-300"
                }`}
              >
                {svc} <span className="opacity-50">{count}</span>
              </button>
            ),
          )}
        </div>
      )}

      {/* Empty state */}
      {!data && !loading && (
        <div className="fade-up flex flex-col items-center justify-center py-24 border border-dashed border-white/[0.08] rounded-2xl text-center space-y-3">
          <div className="text-slate-500 text-[13px]">No resource data</div>
          <div
            className="text-slate-600 text-[12px]"
            dangerouslySetInnerHTML={{
              __html: "Click &ldquo;Fetch resources&rdquo; to collect from AWS",
            }}
          />
        </div>
      )}

      {/* Main content */}
      {data && !loading && (
        <div className="fade-up flex gap-4">
          {/* Resource list */}
          <div className="flex-1 min-w-0 border border-white/[0.06] rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between">
              <span className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">
                {service.toUpperCase()} — {resources.length} resources
              </span>
            </div>

            {resources.length === 0 ? (
              <div className="py-12 text-center text-[12px] text-slate-600">
                No {service.toUpperCase()} resources found in this account
              </div>
            ) : (
              <div className="divide-y divide-white/[0.04]">
                {resources.map((r: any, i: number) => (
                  <button
                    key={i}
                    onClick={() => setSelected(r)}
                    className={`w-full text-left px-4 py-3 transition-colors text-[12px]
                      ${selected === r ? "bg-emerald-500/[0.06]" : "hover:bg-white/[0.02]"}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/40 flex-shrink-0" />
                      <div className="font-mono text-slate-300 truncate">
                        {r.resource_id}
                      </div>
                      <div className="ml-auto text-[10px] text-slate-600 uppercase font-mono flex-shrink-0">
                        {r.region}
                      </div>
                    </div>
                    {r.resource_name && r.resource_name !== r.resource_id && (
                      <div className="ml-4 text-[11px] text-slate-600 mt-0.5 truncate">
                        {r.resource_name}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* JSON detail */}
          {selected && (
            <div className="w-96 flex-shrink-0 bg-[#0d0d14] border border-white/[0.06] rounded-xl overflow-hidden self-start">
              <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
                <span className="text-[11px] text-slate-500 font-mono truncate">
                  {selected.resource_id}
                </span>
                <button
                  onClick={() => setSelected(null)}
                  className="text-slate-600 hover:text-slate-300 flex-shrink-0 ml-2"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path
                      d="M1.5 1.5L10.5 10.5M10.5 1.5L1.5 10.5"
                      stroke="currentColor"
                      strokeWidth="1.3"
                      strokeLinecap="round"
                    />
                  </svg>
                </button>
              </div>
              <div className="p-4 overflow-auto max-h-[70vh]">
                <pre className="text-[10px] text-slate-400 font-mono leading-relaxed whitespace-pre-wrap">
                  {JSON.stringify(selected, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
