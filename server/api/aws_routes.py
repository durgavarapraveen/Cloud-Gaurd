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
def scan_aws(

    regions: Optional[List[str]] = Query(default=None),

    services: Optional[List[str]] = Query(default=None),

    severities: Optional[List[str]] = Query(default=None)

):

    return validate_aws(

        regions=regions,

        services=services,

        severities=severities

    )


# ──────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────

@router.get("/summary")
def aws_summary(

    regions: Optional[List[str]] = Query(default=None)

):

    return get_summary(

        regions=regions

    )


# ──────────────────────────────────────────────
# FAILED FINDINGS
# ──────────────────────────────────────────────

@router.get("/failed")
def aws_failed(

    regions: Optional[List[str]] = Query(default=None)

):

    return get_failed_findings(

        regions=regions

    )


# ──────────────────────────────────────────────
# SEVERITY FILTER
# ──────────────────────────────────────────────

@router.get("/severity/{severity}")
def severity_filter(

    severity: str,

    regions: Optional[List[str]] = Query(default=None)

):

    return get_findings_by_severity(

        severity=severity,

        regions=regions

    )


# ──────────────────────────────────────────────
# SERVICE FILTER
# ──────────────────────────────────────────────

@router.get("/service/{service}")
def service_filter(

    service: str,

    regions: Optional[List[str]] = Query(default=None)

):

    return get_findings_by_service(

        service=service,

        regions=regions

    )
    
# ──────────────────────────────────────────────
# LOAD POLICIES
# ──────────────────────────────────────────────