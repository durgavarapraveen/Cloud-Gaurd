import boto3
import json
import os
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from utils import safe_call


# Importing Scanners for different Services
from Individual_resources.rds import scan_rds
from Individual_resources.s3 import scan_s3
from Individual_resources.ec2 import scan_ec2
from Individual_resources.iam import scan_iam

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  SESSION
# ─────────────────────────────────────────────

def get_session():
    profile = os.getenv("AWS_PROFILE", "cloudguard-scanner")
    return boto3.Session(profile_name=profile)



# ─────────────────────────────────────────────
#  MAIN COLLECTOR — runs all scanners in parallel
# ─────────────────────────────────────────────

def collect_all(regions=None):
    """
    Runs all service scanners in parallel using ThreadPoolExecutor.
    Returns a single dict with all resources grouped by service.

    Args:
        regions: list of AWS regions to scan.
                 Defaults to ['ap-south-1'] if not provided.

    Returns:
        {
            "scan_metadata": { ... },
            "resources": {
                "s3": [...],
                "ec2": [...],
                "iam": [...],
                "rds": [...],
                "cloudtrail": [...]
            },
            "summary": {
                "total_resources": 42,
                "by_service": { "s3": 3, "ec2": 15, ... }
            }
        }
    """
    if regions is None:
        regions = [os.getenv("AWS_DEFAULT_REGION", "ap-south-1")]

    session = get_session()

    # Confirm identity before scanning
    sts = session.client("sts")
    identity = safe_call(sts.get_caller_identity)
    account_id = identity.get("Account") if identity else "unknown"
    logger.info(f"Scanning account: {account_id} | regions: {regions}")

    # Build a list of (task_name, function, args) tuples
    # Each tuple becomes one parallel task
    tasks = []

    # Global services (no region needed)
    tasks.append(("s3",        scan_s3,         (session,)))
    tasks.append(("iam",       scan_iam,         (session,)))

    # Regional services — one task per region
    for region in regions:
        tasks.append((f"ec2_{region}",         scan_ec2,         (session, region)))
        tasks.append((f"rds_{region}",         scan_rds,         (session, region)))
        # tasks.append((f"cloudtrail_{region}",  scan_cloudtrail,  (session, region)))

    # Run all tasks in parallel — max 10 threads
    raw_results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_name = {
            executor.submit(fn, *args): name
            for name, fn, args in tasks
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                raw_results[name] = future.result()
            except Exception as e:
                logger.error(f"Scanner {name} failed: {e}")
                raw_results[name] = []

    # Merge regional results into service buckets
    merged = {
        "s3":         raw_results.get("s3", []),
        "iam":        raw_results.get("iam", []),
        "ec2":        [],
        "rds":        [],
    }
    for region in regions:
        merged["ec2"]        += raw_results.get(f"ec2_{region}", [])
        merged["rds"]        += raw_results.get(f"rds_{region}", [])

    # Build summary counts
    by_service = {svc: len(resources) for svc, resources in merged.items()}
    total = sum(by_service.values())

    output = {
        "scan_metadata": {
            "account_id":  account_id,
            "regions":     regions,
            "scanned_at":  datetime.now(timezone.utc).isoformat(),
            "scanner":     "CloudGuard v0.1",
        },
        "resources": merged,
        "summary": {
            "total_resources": total,
            "by_service": by_service,
        },
    }

    logger.info(f"Scan complete — {total} total resources found")
    return output


# ─────────────────────────────────────────────
#  ENTRY POINT — run directly to test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    results = collect_all(regions=["ap-south-1"])

    # Pretty print the full JSON
    print(json.dumps(results, indent=2, default=str))

    # Also save to a file so you can inspect it
    output_path = "scan_output.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nSaved to {output_path}")
    print(f"\nSummary:")
    for svc, count in results["summary"]["by_service"].items():
        print(f"  {svc:15} {count} resources")
    print(f"  {'TOTAL':15} {results['summary']['total_resources']} resources")