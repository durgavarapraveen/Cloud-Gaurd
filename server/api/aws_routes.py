from fastapi import APIRouter, Query
from typing import List, Optional

from engine.validator.aws_validator import (
    validate_aws,
    get_summary,
    get_failed_findings,
    get_findings_by_severity,
    get_findings_by_service
)

router = APIRouter(
    prefix="/aws",
    tags=["AWS Security Scanner"]
)


# ──────────────────────────────────────────────
# FULL SCAN
# ──────────────────────────────────────────────

@router.get("/scan")
async def scan_aws(

    regions: Optional[List[str]] = Query(default=None),

    services: Optional[List[str]] = Query(default=None),

    severities: Optional[List[str]] = Query(default=None)

):

    return await validate_aws(

        regions=regions,

        services=services,

        severities=severities

    )


# ──────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────

@router.get("/summary")
async def aws_summary(

    regions: Optional[List[str]] = Query(default=None)

):

    return await get_summary(

        regions=regions

    )


# ──────────────────────────────────────────────
# FAILED FINDINGS
# ──────────────────────────────────────────────

@router.get("/failed")
async def aws_failed(

    regions: Optional[List[str]] = Query(default=None)

):

    return await get_failed_findings(

        regions=regions

    )


# ──────────────────────────────────────────────
# SEVERITY FILTER
# ──────────────────────────────────────────────

@router.get("/severity/{severity}")
async def severity_filter(

    severity: str,

    regions: Optional[List[str]] = Query(default=None)

):

    return await get_findings_by_severity(

        severity=severity,

        regions=regions

    )


# ──────────────────────────────────────────────
# SERVICE FILTER
# ──────────────────────────────────────────────

@router.get("/service/{service}")
async def service_filter(

    service: str,

    regions: Optional[List[str]] = Query(default=None)

):

    return await get_findings_by_service(

        service=service,

        regions=regions

    )
    
# ──────────────────────────────────────────────
# LOAD POLICIES
# ──────────────────────────────────────────────