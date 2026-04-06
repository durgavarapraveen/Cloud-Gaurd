import os
import json
import logging
from datetime import datetime, timezone

from scanners.AWS.aws_scanner import collect_all
from engine.checker.aws_checker import run_checks, Status
from yaml_loader.yaml_loader import get_policies

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CORE VALIDATION ENGINE
# ──────────────────────────────────────────────

async def validate_aws(
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
        # rules = load_policies()
        mongo_docs = await get_policies()
        rules = flatten_mongo_rules(mongo_docs)

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

async def get_summary(regions=None):

    results = await validate_aws(
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

async def get_failed_findings(regions=None):

    results = await validate_aws(
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

async def get_findings_by_severity(
        severity,
        regions=None
):

    results = await validate_aws(
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

async def get_findings_by_service(
        service,
        regions=None
):

    results = await validate_aws(
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
    
    
def flatten_mongo_rules(docs):

    rules = []

    for doc in docs:

        provider = doc.get("provider")
        service = doc.get("service")

        yaml_data = doc.get("data", {})

        for rule in yaml_data.get("rules", []):

            rule["provider"] = provider
            rule["service"] = service
            rule["_source_file"] = f"mongo:{doc['_id']}"

            rules.append(rule)

    return rules