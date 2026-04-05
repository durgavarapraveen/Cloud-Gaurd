import boto3
import os
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import json
import pandas as pd
from io import BytesIO
from fastapi.responses import StreamingResponse

from scanners.AWS.utils import safe_call

# Service scanners
from scanners.AWS.Individual_resources.rds import scan_rds
from scanners.AWS.Individual_resources.s3 import scan_s3
from scanners.AWS.Individual_resources.ec2 import scan_ec2
from scanners.AWS.Individual_resources.iam import scan_iam

load_dotenv()

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────

def get_session():
    profile = os.getenv("AWS_PROFILE", "cloudguard-scanner")
    return boto3.Session(profile_name=profile)


# ─────────────────────────────────────────────
# MAIN COLLECTOR
# ─────────────────────────────────────────────

def collect_all(regions=None, services=None):
    """
    Collect AWS resources for requested services.

    :param services: List of services to scan, e.g., ["s3", "ec2"], or None/["ALL"] for all.
    :param regions: List of regions to scan, default is AWS_DEFAULT_REGION.
    """

    if regions is None:
        regions = [os.getenv("AWS_DEFAULT_REGION", "ap-south-1")]
        
    if services is None or "ALL" in services:
        services = ["s3", "iam", "ec2", "rds"]

    session = get_session()

    # Identity check
    sts = session.client("sts")
    identity = safe_call(sts.get_caller_identity)
    account_id = identity.get("Account") if identity else "unknown"

    # logger.info(f"Scanning account {account_id}")

    tasks = []

    # Global services
    if "s3" in services:
        tasks.append(("s3", scan_s3, (session,)))
    if "iam" in services:
        tasks.append(("iam", scan_iam, (session,)))

    # Regional services
    for region in regions:
        if "ec2" in services:
            tasks.append((f"ec2_{region}", scan_ec2, (session, region)))
        if "rds" in services:
            tasks.append((f"rds_{region}", scan_rds, (session, region)))

    raw_results = {}

    with ThreadPoolExecutor(max_workers=10) as executor:

        future_map = {
            executor.submit(fn, *args): name
            for name, fn, args in tasks
        }

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                raw_results[name] = future.result()
            except Exception as e:
                logger.error(f"{name} failed : {str(e)}")
                raw_results[name] = []

    # Merge results
    merged = {svc: [] for svc in services}

    for svc in ["s3", "iam"]:
        if svc in services:
            merged[svc] = raw_results.get(svc, [])
    for region in regions:
        if "ec2" in services:
            merged["ec2"] += raw_results.get(f"ec2_{region}", [])
        if "rds" in services:
            merged["rds"] += raw_results.get(f"rds_{region}", [])

    # Summary
    by_service = {svc: len(merged[svc]) for svc in merged if svc in services}
    total = sum(by_service.values())

    result = {
        "scan_metadata": {
            "account_id": account_id,
            "regions": regions,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "scanner": "CloudGuard"
        },
        "resources": {svc: merged[svc] for svc in services},
        "summary": {
            "total_resources": total,
            "by_service": by_service
        }
    }

    # logger.info(f"Scan finished : {total} resources")
    return result

def flatten_value(val):
    """
    Converts any value that pandas cannot write to an Excel cell
    into a plain string.
 
    Rules:
      - dict  → JSON string   e.g. {"Key": "env"} → '{"Key": "env"}'
      - list  → JSON string   e.g. ["sg-123"]     → '["sg-123"]'
      - None  → empty string
      - bool, int, float, str → left as-is (Excel handles these natively)
    """
    if val is None:
        return ""
    if isinstance(val, (dict, list)):
        return json.dumps(val, default=str)
    return val
 
 
def flatten_record(record: dict) -> dict:
    """
    Applies flatten_value to every value in a resource dict.
    Does NOT recurse — AWS resource dicts are one level deep after
    the scanner runs, so a single pass is enough.
    """
    return {k: flatten_value(v) for k, v in record.items()}


async def export_resources(regions=None, services=None):
 
    result = collect_all(regions, services)
 
    resources = result["resources"]
    summary   = result["summary"]
 
    output = BytesIO()
 
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
 
        # ── Summary sheet ──────────────────────────────────────
        summary_df = pd.DataFrame(
            list(summary["by_service"].items()),
            columns=["Service", "Resource Count"]
        )
        summary_df.loc[len(summary_df)] = [
            "TOTAL",
            summary["total_resources"]
        ]
        summary_df.to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )
 
        # ── One sheet per service ──────────────────────────────
        for service, data in resources.items():
 
            if not data:
                continue
 
            # FIX — flatten every record before passing to DataFrame
            # This converts dicts/lists in cells to JSON strings
            flat_data = [flatten_record(record) for record in data]
 
            df = pd.DataFrame(flat_data)
 
            # Reorder important columns first
            priority_cols = [
                "resource_id",
                "resource_name",
                "region",
                "resource_type",
            ]
            cols = (
                priority_cols +
                [c for c in df.columns if c not in priority_cols]
            )
            df = df[[c for c in cols if c in df.columns]]
 
            # Excel sheet name max length is 31 chars
            sheet_name = service.upper()[:31]
 
            df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False
            )
 
    output.seek(0)
 
    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                "attachment; filename=cloudguard_resources.xlsx"
        }
    )