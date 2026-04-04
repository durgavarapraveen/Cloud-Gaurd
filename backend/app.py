import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

# ── make sure backend/ is on the path when run from any directory ──
sys.path.insert(0, str(Path(__file__).parent))

from scanners.AWS.aws_scanner import collect_all
from backend.engine.loader.aws_loader import load_policies, summarise_policies
from engine.checker.aws_checker import run_checks, Status

# ──────────────────────────────────────────────
#  LOGGING SETUP
# ──────────────────────────────────────────────

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    # Keep boto3 / urllib3 quiet unless verbose
    if not verbose:
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  TERMINAL COLOURS  (Windows CMD compatible)
# ──────────────────────────────────────────────

def supports_colour():
    """
    Returns True if the terminal supports ANSI colour codes.
    Windows CMD does NOT support them by default — falls back to plain text.
    """
    if sys.platform == "win32":
        # Windows 10 1607+ supports ANSI in CMD if VT processing is enabled.
        # Safest to just disable colours on Windows to avoid garbage output.
        return os.environ.get("FORCE_COLOR", "").lower() in ("1", "true", "yes")
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


USE_COLOUR = supports_colour()

COLOURS = {
    "reset":    "\033[0m"    if USE_COLOUR else "",
    "bold":     "\033[1m"    if USE_COLOUR else "",
    "red":      "\033[91m"   if USE_COLOUR else "",
    "green":    "\033[92m"   if USE_COLOUR else "",
    "yellow":   "\033[93m"   if USE_COLOUR else "",
    "blue":     "\033[94m"   if USE_COLOUR else "",
    "magenta":  "\033[95m"   if USE_COLOUR else "",
    "cyan":     "\033[96m"   if USE_COLOUR else "",
    "white":    "\033[97m"   if USE_COLOUR else "",
    "dim":      "\033[2m"    if USE_COLOUR else "",
}

SEV_COLOURS = {
    "CRITICAL": COLOURS["red"]     + COLOURS["bold"],
    "HIGH":     COLOURS["red"],
    "MEDIUM":   COLOURS["yellow"],
    "LOW":      COLOURS["cyan"],
    "INFO":     COLOURS["dim"],
}

STATUS_COLOURS = {
    "PASS":  COLOURS["green"],
    "FAIL":  COLOURS["red"],
    "ERROR": COLOURS["yellow"],
    "SKIP":  COLOURS["dim"],
}

def col(text, colour_key):
    return f"{COLOURS.get(colour_key, '')}{text}{COLOURS['reset']}"

def sev_col(severity):
    c = SEV_COLOURS.get(severity, "")
    return f"{c}{severity:<8}{COLOURS['reset']}"

def status_col(status):
    c = STATUS_COLOURS.get(status, "")
    return f"{c}{status:<5}{COLOURS['reset']}"


# ──────────────────────────────────────────────
#  PRINTER HELPERS
# ──────────────────────────────────────────────

WIDTH = 90

def divider(char="─"):
    print(char * WIDTH)

def header(title):
    print()
    divider("═")
    print(f"  {col(title, 'bold')}")
    divider("═")


def print_scan_header(account_id, regions, rule_count, resource_count):
    print()
    divider("═")
    print(f"  {col('CLOUDGUARD — AWS Security Posture Scan', 'bold')}")
    divider("═")
    print(f"  {'Account':<18} {account_id}")
    print(f"  {'Regions':<18} {', '.join(regions)}")
    print(f"  {'Rules loaded':<18} {rule_count}")
    print(f"  {'Resources found':<18} {resource_count}")
    print(f"  {'Started at':<18} {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    divider("─")


def print_findings_table(findings, show_pass=False):
    """
    Prints a compact findings table sorted by severity then FAIL-first.
    Pass show_pass=True to include PASS results in the table.
    """
    SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

    display = [
        f for f in findings
        if f["status"] != "SKIP" and (show_pass or f["status"] != "PASS")
    ]

    if not display:
        print(f"\n  {col('No findings to display.', 'dim')}")
        return

    # Sort: severity first, then FAIL before PASS
    display.sort(key=lambda f: (
        SEV_ORDER.get(f["severity"], 9),
        0 if f["status"] == "FAIL" else 1,
    ))

    header("FINDINGS TABLE")

    # Column widths
    C = {"status": 6, "sev": 9, "rule": 18, "resource": 34, "region": 13}

    # Table header row
    h_status   = f"{'STATUS':<{C['status']}}"
    h_sev      = f"{'SEVERITY':<{C['sev']}}"
    h_rule     = f"{'RULE ID':<{C['rule']}}"
    h_resource = f"{'RESOURCE':<{C['resource']}}"
    h_region   = f"{'REGION':<{C['region']}}"
    print(f"  {col(h_status, 'bold')} {col(h_sev, 'bold')} {col(h_rule, 'bold')} {col(h_resource, 'bold')} {col(h_region, 'bold')}")
    print(f"  {'─'*C['status']} {'─'*C['sev']} {'─'*C['rule']} {'─'*C['resource']} {'─'*C['region']}")

    for f in display:
        status   = status_col(f["status"])
        sev      = sev_col(f["severity"])
        rule_id  = (f["rule_id"]     or "")[:C["rule"]]
        resource = (f["resource_id"] or "")[:C["resource"]]
        region   = (f["region"]      or "")[:C["region"]]
        print(f"  {status} {sev} {rule_id:<{C['rule']}} {resource:<{C['resource']}} {region:<{C['region']}}")

    print(f"\n  {col(str(len(display)), 'bold')} findings shown  "
          f"({sum(1 for f in display if f['status'] == 'FAIL')} failed, "
          f"{sum(1 for f in display if f['status'] == 'PASS')} passed)")


def print_failures_detail(findings):
    """
    For every FAIL finding, prints a detailed block with the rule title,
    actual value found, and the remediation steps.
    """
    failures = [f for f in findings if f["status"] == "FAIL"]
    if not failures:
        return

    SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    failures.sort(key=lambda f: SEV_ORDER.get(f["severity"], 9))

    header("FAILED CHECKS — DETAIL")

    for i, f in enumerate(failures, 1):
        sev_str  = sev_col(f["severity"])
        rule_str = col(f["rule_id"], "bold")
        print(f"\n  [{i}] {rule_str}  {sev_str}")
        print(f"      {col(f['rule_title'], 'white')}")
        divider("·" * WIDTH)
        print(f"  {'Resource':<14} {f['resource_id']}  ({f['region']})")
        print(f"  {'Type':<14} {f['resource_type']}")
        print(f"  {'Check path':<14} {f.get('operator')}  →  {f['actual_value']}")
        print(f"  {'Expected':<14} operator={f['operator']}  value={f['expected_value']}")

        remediation = (f.get("remediation") or "").strip()
        if remediation:
            # Word-wrap remediation at 72 chars
            words = remediation.split()
            lines, current = [], []
            for word in words:
                if sum(len(w) + 1 for w in current) + len(word) > 72:
                    lines.append(" ".join(current))
                    current = [word]
                else:
                    current.append(word)
            if current:
                lines.append(" ".join(current))
            print(f"  {'Fix':<14} {lines[0]}")
            for line in lines[1:]:
                print(f"  {'':<14} {line}")


def print_summary(summary, scan_metadata):
    """
    Prints the final compliance score and breakdown.
    """
    header("SCAN SUMMARY")

    score = summary["score"]

    # Score display
    if score >= 90:
        score_str = col(f"{score}%", "green")
        grade = col("GOOD", "green")
    elif score >= 70:
        score_str = col(f"{score}%", "yellow")
        grade = col("NEEDS ATTENTION", "yellow")
    else:
        score_str = col(f"{score}%", "red")
        grade = col("CRITICAL ISSUES", "red")

    print(f"\n  Compliance score  :  {score_str}  {grade}")
    print()
    print(f"  Total checks      :  {summary['total']}")
    print(f"  {col('Passed', 'green')}            :  {summary['passed']}")
    print(f"  {col('Failed', 'red')}            :  {summary['failed']}")
    print(f"  Errored           :  {summary['errored']}")

    # Failed breakdown by severity
    print(f"\n  {col('Failed by severity:', 'bold')}")
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        count = summary["by_severity"].get(sev, 0)
        if count > 0:
            bar = col("█" * min(count, 30), SEV_COLOURS.get(sev, ""))
            print(f"    {sev:<10}  {count:>3}  {bar}")

    # Checks by service
    print(f"\n  {col('Checks by service:', 'bold')}")
    for svc, count in summary["by_service"].items():
        failed_in_svc = sum(
            1 for k, v in summary.get("_failed_by_service", {}).items()
            if k == svc for _ in range(v)
        )
        print(f"    {svc:<15}  {count:>3} checks")

    print(f"\n  Scanned at  :  {scan_metadata.get('scanned_at', 'unknown')}")
    print(f"  Account     :  {scan_metadata.get('account_id', 'unknown')}")
    print(f"  Regions     :  {', '.join(scan_metadata.get('regions', []))}")
    print()
    divider("═")
    print()


def print_policy_summary(rules):
    """
    Prints a quick summary of loaded policy rules before scanning.
    """
    summary = summarise_policies(rules)
    print(f"\n  {col('Policy rules loaded:', 'bold')} {summary['total_rules']}")
    for svc, count in summary["by_service"].items():
        print(f"    {svc:<15}  {count} rules")


# ──────────────────────────────────────────────
#  EXPORT
# ──────────────────────────────────────────────

def export_json(results, output_path):
    """Saves the full scan results to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results saved to {output_path}")
    print(f"\n  {col('Results saved to:', 'bold')} {output_path}")


def export_csv(findings, output_path):
    """Saves findings to a CSV file — easy to open in Excel."""
    import csv
    fields = [
        "status", "severity", "rule_id", "rule_title",
        "service", "resource_type", "resource_id",
        "region", "actual_value", "operator",
        "expected_value", "remediation", "checked_at",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(findings)
    print(f"  {col('CSV saved to:', 'bold')} {output_path}")


# ──────────────────────────────────────────────
#  CLI ARGUMENT PARSER
# ──────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog="cloudguard",
        description="CloudGuard — AWS Security Posture Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --regions ap-south-1 us-east-1
  python main.py --severity CRITICAL HIGH
  python main.py --service s3
  python main.py --show-pass
  python main.py --output results.json
  python main.py --csv findings.csv
  python main.py --verbose
        """,
    )

    parser.add_argument(
        "--regions",
        nargs="+",
        default=None,
        metavar="REGION",
        help="AWS regions to scan (default: ap-south-1 from .env)",
    )
    parser.add_argument(
        "--severity",
        nargs="+",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
        default=None,
        metavar="SEV",
        help="Only show findings at these severity levels",
    )
    parser.add_argument(
        "--service",
        nargs="+",
        default=None,
        metavar="SERVICE",
        help="Only scan these services e.g. --service s3 ec2",
    )
    parser.add_argument(
        "--show-pass",
        action="store_true",
        help="Include PASS results in the findings table",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Save full results to a JSON file",
    )
    parser.add_argument(
        "--csv",
        metavar="FILE",
        help="Save findings to a CSV file (opens in Excel)",
    )
    parser.add_argument(
        "--no-detail",
        action="store_true",
        help="Skip the detailed failure block — only show the table",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show DEBUG logs including boto3 calls",
    )

    return parser


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    parser = build_parser()
    args   = parser.parse_args()

    setup_logging(verbose=args.verbose)

    # ── 1. Load policy rules ───────────────────────────────────────────
    logger.info("Loading policy rules...")
    try:
        all_rules = load_policies()
    except FileNotFoundError as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)

    if not all_rules:
        print("\n  ERROR: No rules loaded. Add YAML files to backend/policies/")
        sys.exit(1)

    # Filter rules by --service flag if provided
    if args.service:
        all_rules = [r for r in all_rules if r.get("service") in args.service]
        if not all_rules:
            print(f"\n  ERROR: No rules found for services: {args.service}")
            sys.exit(1)

    # ── 2. Collect AWS resources ───────────────────────────────────────
    regions = args.regions or [os.getenv("AWS_DEFAULT_REGION", "ap-south-1")]
    logger.info(f"Starting AWS resource collection for regions: {regions}")

    try:
        raw_data = collect_all(regions=regions)
    except Exception as e:
        print(f"\n  ERROR collecting AWS resources: {e}")
        logger.exception("Collection failed")
        sys.exit(1)

    scan_metadata  = raw_data.get("scan_metadata", {})
    resource_summary = raw_data.get("summary", {})
    total_resources  = resource_summary.get("total_resources", 0)

    # Print scan header after collection so we have real counts
    print_scan_header(
        account_id     = scan_metadata.get("account_id", "unknown"),
        regions        = regions,
        rule_count     = len(all_rules),
        resource_count = total_resources,
    )
    print_policy_summary(all_rules)

    # ── 3. Run checks ──────────────────────────────────────────────────
    logger.info("Running checks...")
    print(f"\n  {col('Running checks...', 'dim')}")

    try:
        results = run_checks(raw_data, all_rules)
    except Exception as e:
        print(f"\n  ERROR running checks: {e}")
        logger.exception("Check engine failed")
        sys.exit(1)

    findings = results["findings"]
    summary  = results["summary"]

    # Apply --severity filter to display (not to the scan itself)
    display_findings = findings
    if args.severity:
        display_findings = [
            f for f in findings
            if f["severity"] in args.severity
        ]

    # ── 4. Print results ───────────────────────────────────────────────
    print_findings_table(display_findings, show_pass=args.show_pass)

    if not args.no_detail:
        print_failures_detail(display_findings)

    print_summary(summary, scan_metadata)

    # ── 5. Export if requested ─────────────────────────────────────────
    if args.output:
        full_results = {
            "scan_metadata": scan_metadata,
            "summary":       summary,
            "findings":      findings,
            "resources":     raw_data.get("resources", {}),
        }
        export_json(full_results, args.output)

    if args.csv:
        export_csv(findings, args.csv)

    # ── 6. Exit code — non-zero if any CRITICAL or HIGH failures ───────
    critical_high_failures = [
        f for f in findings
        if f["status"] == "FAIL" and f["severity"] in ("CRITICAL", "HIGH")
    ]
    if critical_high_failures:
        sys.exit(1)   # useful for CI/CD pipelines — fails the pipeline
    sys.exit(0)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)