import { Severity } from "@/lib/api";

const config: Record<Severity, { bg: string; text: string; dot: string }> = {
  CRITICAL: {
    bg: "bg-red-500/10 border border-red-500/30",
    text: "text-red-400",
    dot: "bg-red-400",
  },
  HIGH: {
    bg: "bg-orange-500/10 border border-orange-500/30",
    text: "text-orange-400",
    dot: "bg-orange-400",
  },
  MEDIUM: {
    bg: "bg-yellow-500/10 border border-yellow-500/30",
    text: "text-yellow-400",
    dot: "bg-yellow-400",
  },
  LOW: {
    bg: "bg-green-500/10 border border-green-500/30",
    text: "text-green-400",
    dot: "bg-green-400",
  },
  INFO: {
    bg: "bg-indigo-500/10 border border-indigo-500/30",
    text: "text-indigo-400",
    dot: "bg-indigo-400",
  },
};

export default function SeverityBadge({
  severity,
  size = "sm",
}: {
  severity: Severity;
  size?: "xs" | "sm";
}) {
  const c = config[severity] ?? config["INFO"];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded px-2 py-0.5 font-mono
        ${c.bg} ${c.text}
        ${size === "xs" ? "text-[10px]" : "text-[11px]"}
      `}
    >
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${c.dot}`} />
      {severity}
    </span>
  );
}
