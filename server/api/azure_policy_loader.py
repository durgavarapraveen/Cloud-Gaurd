from fastapi import APIRouter
from engine.loader.azure_loader import (
    load_policies,
    summarise_policies,
    get_rules_by_severity,
    get_rules_for_service
)

router = APIRouter(
    prefix="/azure/policies",
    tags=["Azure Policies"]
)


# ──────────────────────────────────────────────
# GET ALL RULES
# ──────────────────────────────────────────────

@router.get("/")
def get_all_policies():

    rules = load_policies()

    return {

        "success":True,

        "total":len(rules),

        "rules":rules

    }


# ──────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────

@router.get("/summary")
def policies_summary():

    rules = load_policies()

    return {

        "success":True,

        "summary":
            summarise_policies(rules)

    }


# ──────────────────────────────────────────────
# SERVICE FILTER
# ──────────────────────────────────────────────

@router.get("/service/{service}")
def policies_by_service(service:str):

    rules = load_policies()

    filtered = get_rules_for_service(
        rules,
        service
    )

    return {

        "success":True,

        "count":len(filtered),

        "rules":filtered

    }


# ──────────────────────────────────────────────
# SEVERITY FILTER
# ──────────────────────────────────────────────

@router.get("/severity/{severity}")
def policies_by_severity(severity:str):

    rules = load_policies()

    filtered = get_rules_by_severity(
        rules,
        severity
    )

    return {

        "success":True,

        "count":len(filtered),

        "rules":filtered

    }