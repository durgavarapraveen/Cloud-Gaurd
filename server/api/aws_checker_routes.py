from fastapi import APIRouter
from engine.checker.aws_checker import (
    scan_aws_resources,
    get_summary,
    get_failed_findings,
    get_findings_by_severity
)

router = APIRouter(
    prefix="/aws/checker",
    tags=["AWS Validator"]
)


# Full scan
@router.get("/scan")
def scan():

    return scan_aws_resources()


# Only summary
@router.get("/summary")
def summary():

    return get_summary()


# Only failed findings
@router.get("/failed")
def failed():

    return {
        "failed_findings": get_failed_findings()
    }


# Filter by severity
@router.get("/severity/{severity}")
def by_severity(severity: str):

    return {
        "severity": severity,
        "findings": get_findings_by_severity(severity)
    }