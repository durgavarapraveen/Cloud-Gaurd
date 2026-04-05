import jmespath
import logging
from datetime import datetime, timezone
from enum import Enum
from yaml_loader.yaml_loader import get_policies

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  CONSTANTS
# ──────────────────────────────────────────────

class Status(str, Enum):
    PASS  = "PASS"
    FAIL  = "FAIL"
    ERROR = "ERROR"   # rule could not be evaluated (e.g. path resolution failed)
    SKIP  = "SKIP"    # resource type does not match this rule


# ──────────────────────────────────────────────
#  OPERATORS
#  Each function receives (actual_value, expected_value)
#  and returns True (pass) or False (fail).
# ──────────────────────────────────────────────

def _op_exists(value, _expected):
    """
    PASS if the value is present and not None.
    Used for: encryption enabled, logging configured, MFA devices attached.
    """
    return value is not None


def _op_not_exists(value, _expected):
    """
    PASS if the value is absent (None).
    Used for: root access keys should NOT exist.
    """
    return value is None


def _op_equals(value, expected):
    """
    PASS if value exactly matches expected.
    Case-sensitive string comparison, also works for booleans and integers.
    Used for: versioning.Status == "Enabled"
    """
    return value == expected


def _op_not_equals(value, expected):
    """
    PASS if value does NOT match expected.
    Used for: versioning.Status != "Suspended"
    """
    return value != expected


def _op_is_true(value, _expected):
    """
    PASS if value is boolean True.
    Handles both Python bool True and string "true" / "True".
    Used for: BlockPublicAcls is true, MultiAZ is true.
    """
    if isinstance(value, bool):
        return value is True
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def _op_is_false(value, _expected):
    """
    PASS if value is boolean False.
    Used for: publicly_accessible is false, IsDefault VPC is false.
    """
    if isinstance(value, bool):
        return value is False
    if isinstance(value, str):
        return value.lower() == "false"
    # None / missing counts as not-true, but we treat it as a separate case
    return False


def _op_contains(value, expected):
    """
    PASS if value contains expected.
    Works for:
      - strings  : "AES256" in "AES256"  → True
      - lists    : "0.0.0.0/0" in ["10.0.0.0/8", "0.0.0.0/0"]  → True
      - dicts    : checks if expected is a key in the dict
    Used for: encryption algorithm contains "AES256", CIDR list contains bad range.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return str(expected) in value
    if isinstance(value, list):
        return expected in value
    if isinstance(value, dict):
        return expected in value
    return False


def _op_not_contains(value, expected):
    """
    PASS if value does NOT contain expected.
    Inverse of contains.
    Used for: security group inbound rules should not contain 0.0.0.0/0 on port 22.
    """
    return not _op_contains(value, expected)


def _op_contains_key(value, expected):
    """
    PASS if a list of dicts has at least one item where the 'Key' field
    matches expected.

    AWS tags are stored as: [{"Key": "Environment", "Value": "prod"}, ...]
    So to check that a "cost-center" tag exists:
        path: tags
        operator: contains_key
        value: "cost-center"

    Also handles flat dicts: checks if expected is a key in the dict.
    """
    if value is None:
        return False
    # List of dicts — standard AWS tag format
    if isinstance(value, list):
        return any(
            isinstance(item, dict) and item.get("Key") == expected
            for item in value
        )
    # Plain dict — check if key exists
    if isinstance(value, dict):
        return expected in value
    return False


# Map operator name (from YAML) to its function
OPERATOR_MAP = {
    "exists":        _op_exists,
    "not_exists":    _op_not_exists,
    "equals":        _op_equals,
    "not_equals":    _op_not_equals,
    "is_true":       _op_is_true,
    "is_false":      _op_is_false,
    "contains":      _op_contains,
    "not_contains":  _op_not_contains,
    "contains_key":  _op_contains_key,
}


# ──────────────────────────────────────────────
#  JMESPATH RESOLVER
# ──────────────────────────────────────────────

def resolve_path(resource, path):
    """
    Resolves a JMESPath expression against a resource dict.

    JMESPath lets you navigate nested JSON with dot notation and
    array indexing — the same syntax used in AWS CLI --query.

    Examples:
      "encryption.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm"
        → digs into encryption → Rules list → first item → nested key

      "public_access_block.BlockPublicAcls"
        → digs into public_access_block dict → BlockPublicAcls field

      "versioning.Status"
        → top-level versioning dict → Status field

      "tags"
        → returns the entire tags list as-is

    Returns None if the path does not resolve (key missing or null).
    Raises nothing — errors are caught by run_check().
    """
    try:
        return jmespath.search(path, resource)
    except jmespath.exceptions.JMESPathError as e:
        logger.debug(f"JMESPath error on path '{path}': {e}")
        return None


# ──────────────────────────────────────────────
#  SINGLE CHECK
# ──────────────────────────────────────────────

def run_check(resource, rule):
    """
    Evaluates one rule against one resource.

    Args:
        resource : dict from aws_collector.py
                   must have keys: resource_type, resource_id, resource_name, region
        rule     : dict from loader.py
                   must have keys: id, title, severity, service, resource_type, check

    Returns a Finding dict:
    {
        "rule_id"       : "CIS-S3-01",
        "rule_title"    : "S3 bucket encryption must be enabled",
        "severity"      : "HIGH",
        "service"       : "s3",
        "resource_type" : "s3_bucket",
        "resource_id"   : "my-bucket-name",
        "resource_name" : "my-bucket-name",
        "region"        : "global",
        "status"        : "PASS" | "FAIL" | "ERROR" | "SKIP",
        "actual_value"  : <whatever jmespath resolved to>,
        "expected_value": <the value field from the rule, if any>,
        "operator"      : "exists",
        "remediation"   : "...",
        "source_file"   : "policies/aws/s3.yaml",
        "checked_at"    : "2026-04-04T10:00:00+00:00"
    }
    """
    rule_resource_type = rule.get("resource_type")
    actual_resource_type = resource.get("resource_type")
    
   
    # Skip if this rule does not apply to this resource type
    # e.g. don't run s3_bucket rules against ec2_instance resources
    if rule_resource_type != actual_resource_type:
        return _make_finding(resource, rule, Status.SKIP, actual_value=None)

    check_block  = rule.get("check", {})
    path         = check_block.get("path")
    operator_key = check_block.get("operator")
    expected     = check_block.get("value")  # optional — not all operators need it
    
    print(f"Running check {rule.get('id')} against resource {resource.get('resource_id')} with operator {operator_key} and path {path}*********************************************************************88")

    # Resolve the path against the resource using JMESPath
    try:
        actual_value = resolve_path(resource, path)
        print(f"Resolved path {path} to actual value: {actual_value}%%%%%%%%%%%%%%%%%%%%%%%%%%%%5")
    except Exception as e:
        logger.error(
            f"[checker] Path resolution failed — "
            f"rule={rule.get('id')} resource={resource.get('resource_id')} "
            f"path={path} error={e}"
        )
        return _make_finding(resource, rule, Status.ERROR, actual_value=None)

    # Look up the operator function
    operator_fn = OPERATOR_MAP.get(operator_key)
    
    if operator_fn is None:
        logger.error(f"[checker] Unknown operator '{operator_key}' in rule {rule.get('id')}")
        return _make_finding(resource, rule, Status.ERROR, actual_value=actual_value)

    # Run the operator — wrap in try/except so one bad resource never crashes the scan
    print(f"Applying operator {operator_key} with actual value {actual_value} and expected value {expected}###########################################################")
    try:
        passed = operator_fn(actual_value, expected)
    except Exception as e:
        logger.error(
            f"[checker] Operator '{operator_key}' raised an exception — "
            f"rule={rule.get('id')} resource={resource.get('resource_id')} "
            f"actual_value={actual_value} error={e}"
        )
        return _make_finding(resource, rule, Status.ERROR, actual_value=actual_value)

    status = Status.PASS if passed else Status.FAIL

    if status == Status.FAIL:
        logger.debug(
            f"FAIL — {rule.get('id')} | {resource.get('resource_id')} | "
            f"path={path} actual={actual_value} expected={expected}"
        )

    return _make_finding(
        resource,
        rule,
        status,
        actual_value=actual_value,
        expected_value=expected,
        operator=operator_key,
    )


def _make_finding(resource, rule, status,
                  actual_value=None, expected_value=None, operator=None):
    """
    Builds the standardised finding dict returned by run_check().
    Centralised here so the shape is always consistent.
    """
    return {
        "rule_id":        rule.get("id"),
        "rule_title":     rule.get("title"),
        "severity":       rule.get("severity"),
        "service":        rule.get("service"),
        "resource_type":  resource.get("resource_type"),
        "resource_id":    resource.get("resource_id"),
        "resource_name":  resource.get("resource_name"),
        "region":         resource.get("region"),
        "status":         status.value,
        "actual_value":   str(actual_value) if actual_value is not None else None,
        "expected_value": str(expected_value) if expected_value is not None else None,
        "operator":       operator or rule.get("check", {}).get("operator"),
        "remediation":    rule.get("remediation", "").strip(),
        "source_file":    rule.get("_source_file"),
        "checked_at":     datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────
#  BULK RUNNER
# ──────────────────────────────────────────────

def run_checks(all_resources, all_rules):
    """
    Runs every applicable rule against every resource.
    Skips SKIP-status findings so the output only contains
    meaningful results (PASS, FAIL, ERROR).

    Args:
        all_resources : flat list of resource dicts from aws_collector.py
                        OR the nested dict — this function handles both shapes:
                        - flat list  : [{"resource_type": "s3_bucket", ...}, ...]
                        - nested dict: {"s3": [...], "ec2": [...], ...}

        all_rules     : flat list of rule dicts from loader.load_policies()

    Returns:
        {
            "findings"  : [ ...finding dicts... ],
            "summary"   : {
                "total"   : 42,
                "passed"  : 30,
                "failed"  : 10,
                "errored" : 2,
                "by_severity": {"CRITICAL": 2, "HIGH": 5, ...},
                "by_service" : {"s3": 10, "ec2": 20, ...},
                "score"      : 75.0    ← percentage of checks that passed
            }
        }
    """
    # Normalise input — handle both flat list and nested dict from collect_all()
    flat_resources = _flatten_resources(all_resources)

    findings = []
    for resource in flat_resources:
        resource_type = resource.get("resource_type")

        # Only run rules whose resource_type matches this resource
        matching_rules = [
            r for r in all_rules
            if r.get("resource_type") == resource_type
        ]
        

        for rule in matching_rules:
            finding = run_check(resource, rule)

            # Drop SKIP findings — they add noise without value
            if finding["status"] == Status.SKIP.value:
                continue

            findings.append(finding)

    summary = _build_summary(findings)

    # logger.info(
    #     f"[checker] Scan complete — "
    #     f"{summary['total']} checks | "
    #     f"{summary['passed']} passed | "
    #     f"{summary['failed']} failed | "
    #     f"score: {summary['score']}%"
    # )

    return {"findings": findings, "summary": summary}


def _flatten_resources(resources):
    """
    Accepts either:
      - a flat list  : [resource, resource, ...]
      - a nested dict: {"s3": [...], "ec2": [...], "resources": {"s3": [...]}}
        (the shape returned by aws_collector.collect_all())

    Always returns a flat list.
    """
    if isinstance(resources, list):
        return resources

    if isinstance(resources, dict):
        # collect_all() returns {"resources": {"s3": [], "ec2": []}, ...}
        if "resources" in resources:
            resources = resources["resources"]

        flat = []
        for service_resources in resources.values():
            if isinstance(service_resources, list):
                flat.extend(service_resources)
        return flat

    # logger.warning(f"[checker] Unexpected resources type: {type(resources)}")
    return []


def _build_summary(findings):
    """
    Builds the summary dict from a list of findings.
    Excludes SKIP and ERROR from the pass-rate calculation.
    """
    from collections import Counter

    passed  = [f for f in findings if f["status"] == Status.PASS.value]
    failed  = [f for f in findings if f["status"] == Status.FAIL.value]
    errored = [f for f in findings if f["status"] == Status.ERROR.value]

    evaluable = len(passed) + len(failed)
    score = round((len(passed) / evaluable) * 100, 1) if evaluable > 0 else 0.0

    # Severity breakdown of FAILED findings only
    failed_severities = Counter(f["severity"] for f in failed)
    by_severity = {
        sev: failed_severities.get(sev, 0)
        for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
    }

    # Total checks (pass + fail) per service
    all_service_counts = Counter(f["service"] for f in findings
                                 if f["status"] != Status.SKIP.value)

    return {
        "total":        len(findings),
        "passed":       len(passed),
        "failed":       len(failed),
        "errored":      len(errored),
        "score":        score,
        "by_severity":  by_severity,
        "by_service":   dict(all_service_counts),
    }


# ──────────────────────────────────────────────
#  ENTRY POINT — run directly to test
# ──────────────────────────────────────────────

async def scan_aws_resources(resources=None, rules=None):
    """
    Main function for API usage.
    This is what Flask/FastAPI will call.

    Args:
        resources (optional): AWS resources dict
        rules (optional): loaded policies

    Returns:
        dict:
        {
            findings: [],
            summary: {}
        }
    """

    try:

        # lazy imports (prevents circular imports)
        if resources is None:
            from scanners.AWS.aws_scanner import collect_all
            resources = collect_all()

        if rules is None:
            # rules = load_policies()
            mongo_docs = await get_policies()

            rules = flatten_mongo_rules(mongo_docs)

        results = run_checks(resources, rules)

        return {
            "success": True,
            "results": results
        }

    except Exception as e:

        logger.error(f"AWS scan failed: {e}")

        return {
            "success": False,
            "error": str(e)
        }


async def get_summary(resources=None, rules=None):

    results = await scan_aws_resources(resources, rules)

    if not results["success"]:
        return results

    return results["results"]["summary"]


async def get_failed_findings(resources=None, rules=None):

    results = await scan_aws_resources(resources, rules)

    if not results["success"]:
        return results

    findings = results["results"]["findings"]

    failed = [
        f for f in findings
        if f["status"] == Status.FAIL.value
    ]

    return failed


async def get_findings_by_severity(severity, resources=None, rules=None):
    results = await scan_aws_resources(resources, rules)
    if not results["success"]:
        return results
    findings = results["results"]["findings"]
    filtered = [
        f for f in findings
        if f["severity"].lower() == severity.lower()
    ]
    return filtered

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