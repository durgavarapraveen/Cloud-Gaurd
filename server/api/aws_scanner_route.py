from fastapi import APIRouter

from scanners.AWS.aws_scanner import (
    collect_all
)

router = APIRouter(
    prefix="/aws/scanner",
    tags=["AWS Security Scanner"]
)


# ──────────────────────────────────────────────
# FULL SCAN
# ──────────────────────────────────────────────

@router.get("/scan/{service}")
def scan_aws(service: str):
    
    service_List = service.split(",") if service else []

    return collect_all(
        regions=None,
        services=service_List if service_List else None
    )
    