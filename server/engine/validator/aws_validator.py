import os
import json
import logging
from datetime import datetime, timezone

from scanners.AWS.aws_scanner import collect_all
from engine.loader.aws_loader import load_policies
from engine.checker.aws_checker import run_checks, Status

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CORE VALIDATION ENGINE
# ──────────────────────────────────────────────

def validate_aws(
        regions=None,
        services=None,
        severities=None
):

    try:

        if not regions:
            regions = [
                os.getenv(
                    "AWS_DEFAULT_REGION",
                    "ap-south-1"
                )
            ]

        # Load rules
        rules = load_policies()

        # Filter rules by service
        if services:

            rules = [

                r for r in rules

                if r.get("service") in services

            ]

        # Collect AWS resources
        resources = collect_all(
            regions=regions
        )

        # Run rule engine
        results = run_checks(
            resources,
            rules
        )

        findings = results.get(
            "findings",
            []
        )

        # Apply severity filter
        if severities:

            findings = [

                f for f in findings

                if f.get("severity") in severities

            ]

        return {

            "success": True,

            "scan_time":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "scan_metadata":
                resources.get(
                    "scan_metadata",
                    {}
                ),

            "summary":
                results.get(
                    "summary",
                    {}
                ),

            "findings":
                findings
        }

    except Exception as e:

        logger.exception(
            "AWS validation failed"
        )

        return {

            "success": False,

            "error": str(e)
        }


# ──────────────────────────────────────────────
# SUMMARY ONLY
# ──────────────────────────────────────────────

def get_summary(regions=None):

    results = validate_aws(
        regions=regions
    )

    if not results["success"]:

        return results

    return {

        "success": True,

        "summary":
            results.get(
                "summary",
                {}
            )
    }


# ──────────────────────────────────────────────
# FAILED FINDINGS
# ──────────────────────────────────────────────

def get_failed_findings(regions=None):

    results = validate_aws(
        regions=regions
    )

    if not results["success"]:

        return results

    failed = [

        f for f in results.get(
            "findings",
            []
        )

        if f.get("status")
        ==
        Status.FAIL.value

    ]

    return {

        "success": True,

        "total_failed":
            len(failed),

        "failures":
            failed
    }


# ──────────────────────────────────────────────
# FILTER BY SEVERITY
# ──────────────────────────────────────────────

def get_findings_by_severity(
        severity,
        regions=None
):

    results = validate_aws(
        regions=regions
    )

    if not results["success"]:

        return results

    findings = [

        f for f in results.get(
            "findings",
            []
        )

        if f.get(
            "severity",
            ""
        ).lower()

        ==

        severity.lower()

    ]

    return {

        "success": True,

        "count":
            len(findings),

        "findings":
            findings
    }


# ──────────────────────────────────────────────
# FILTER BY SERVICE
# ──────────────────────────────────────────────

def get_findings_by_service(
        service,
        regions=None
):

    results = validate_aws(
        regions=regions
    )

    if not results["success"]:

        return results

    findings = [

        f for f in results.get(
            "findings",
            []
        )

        if f.get("service")
        ==
        service

    ]

    return {

        "success": True,

        "count":
            len(findings),

        "findings":
            findings
    }


# ──────────────────────────────────────────────
# EXPORT HELPERS
# ──────────────────────────────────────────────

def export_json(
        results,
        path
):

    try:

        with open(
                path,
                "w",
                encoding="utf-8"
        ) as f:

            json.dump(

                results,
                f,
                indent=2,
                default=str

            )

        return True

    except Exception as e:

        logger.error(e)

        return False


def export_csv(
        findings,
        path
):

    import csv

    fields = [

        "status",
        "severity",

        "rule_id",
        "rule_title",

        "service",

        "resource_type",
        "resource_id",

        "region",

        "actual_value",

        "operator",
        "expected_value",

        "remediation",

        "checked_at"
    ]

    try:

        with open(

                path,
                "w",

                newline="",
                encoding="utf-8"

        ) as f:

            writer = csv.DictWriter(

                f,

                fieldnames=fields,

                extrasaction="ignore"

            )

            writer.writeheader()

            writer.writerows(
                findings
            )

        return True

    except Exception as e:

        logger.error(e)

        return False