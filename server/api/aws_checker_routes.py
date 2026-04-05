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
async def scan():
    return await scan_aws_resources()


# Only summary
@router.get("/summary")
async def summary():

    return await get_summary()


# Only failed findings
@router.get("/failed")
async def failed():

    return {
        "failed_findings": await get_failed_findings()
    }


# Filter by severity
@router.get("/severity/{severity}")
async def by_severity(severity: str):

    return {
        "severity": severity,
        "findings": await get_findings_by_severity(severity)
    }