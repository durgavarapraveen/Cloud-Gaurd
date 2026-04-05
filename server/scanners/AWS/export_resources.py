import json
from io import BytesIO
from datetime import datetime, timezone
import pandas as pd
from fastapi.responses import StreamingResponse
from scanners.AWS.aws_scanner import collect_all


def flatten_value(val):
    """
    Converts any value that pandas cannot write to an Excel cell
    into a plain string or Excel-safe type.

    Rules:
      - dict     → JSON string
      - list     → JSON string
      - None     → empty string
      - datetime with timezone → strip timezone (Excel requirement)
      - datetime string with tz → parse and strip timezone
      - bool, int, float, str  → left as-is
    """
    if val is None:
        return ""

    # datetime object with tzinfo — strip the timezone
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val

    # ISO string that looks like a datetime with timezone
    # e.g. "2024-01-15T10:30:00+00:00" or "2024-01-15T10:30:00Z"
    if isinstance(val, str) and len(val) > 18:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S+00:00",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f+00:00",
            "%Y-%m-%dT%H:%M:%S%z",
        ):
            try:
                dt = datetime.strptime(val, fmt)
                # Return as timezone-naive string Excel can display
                return dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

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