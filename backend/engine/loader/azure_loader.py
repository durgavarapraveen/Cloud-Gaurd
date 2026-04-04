
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  VALIDATION
# ──────────────────────────────────────────────

REQUIRED_FIELDS = {"id", "title", "severity", "service", "resource_type", "check"}
REQUIRED_CHECK_FIELDS = {"path", "operator"}
VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
VALID_OPERATORS = {
    "exists",
    "not_exists",
    "equals",
    "not_equals",
    "is_true",
    "is_false",
    "contains",
    "not_contains",
    "contains_key",
}


def validate_rule(rule, source_file):
    """
    Validates a single rule dict loaded from YAML.
    Returns a list of error strings — empty list means the rule is valid.
    Logs a warning for each problem found but does NOT raise an exception —
    invalid rules are skipped so one bad rule does not break the whole load.
    """
    errors = []

    # Check all required top-level fields exist
    missing = REQUIRED_FIELDS - set(rule.keys())
    if missing:
        errors.append(f"Missing required fields: {missing}")

    # Check severity is a known value
    severity = rule.get("severity", "")
    if severity not in VALID_SEVERITIES:
        errors.append(f"Invalid severity '{severity}' — must be one of {VALID_SEVERITIES}")

    # Check the nested 'check' block
    check = rule.get("check")
    if not isinstance(check, dict):
        errors.append("'check' must be a dict with 'path' and 'operator' keys")
    else:
        missing_check = REQUIRED_CHECK_FIELDS - set(check.keys())
        if missing_check:
            errors.append(f"'check' block missing fields: {missing_check}")

        operator = check.get("operator", "")
        if operator not in VALID_OPERATORS:
            errors.append(f"Unknown operator '{operator}' — must be one of {VALID_OPERATORS}")

        # Operators that require a 'value' field
        needs_value = {"equals", "not_equals", "contains", "not_contains", "contains_key"}
        if operator in needs_value and "value" not in check:
            errors.append(f"Operator '{operator}' requires a 'value' field in the check block")

    if errors:
        rule_id = rule.get("id", "UNKNOWN")
        for err in errors:
            logger.warning(f"[loader] Skipping rule {rule_id} in {source_file}: {err}")

    return errors


# ──────────────────────────────────────────────
#  LOADER
# ──────────────────────────────────────────────

def load_policies(policies_dir=None):
    """
    Walks the entire policies/ directory tree, reads every .yaml file,
    validates each rule, and returns a single flat list of valid rule dicts.

    Each rule dict is enriched with two extra fields before being returned:
      _source_file : relative path of the YAML file it came from
      _rule_index  : position of the rule within that file (for debugging)

    Args:
        policies_dir: path to the policies folder.
                      Defaults to <this file's parent>/../policies

    Returns:
        List of rule dicts, e.g.:
        [
            {
                "id": "CIS-S3-01",
                "title": "S3 bucket encryption must be enabled",
                "severity": "HIGH",
                "service": "s3",
                "resource_type": "s3_bucket",
                "check": {
                    "path": "encryption.Rules[0]...",
                    "operator": "exists"
                },
                "remediation": "...",
                "_source_file": "policies/aws/s3.yaml",
                "_rule_index": 0
            },
            ...
        ]
    """
    if policies_dir is None:
        # Default: resolve relative to this file's location
        # backend/engine/loader.py  →  backend/policies/
        policies_dir = Path(__file__).parent.parent.parent / "policies/azure"

    policies_dir = Path(policies_dir)

    if not policies_dir.exists():
        raise FileNotFoundError(
            f"Policies directory not found: {policies_dir}\n"
            f"Expected structure: backend/policies/aws/s3.yaml"
        )

    all_rules = []
    files_loaded = 0
    files_skipped = 0
    rules_skipped = 0

    # Walk the entire directory tree recursively
    # This picks up policies/aws/s3.yaml, policies/custom/company.yaml, etc.
    yaml_files = sorted(policies_dir.rglob("*.yaml"))

    if not yaml_files:
        logger.warning(f"[loader] No .yaml files found in {policies_dir}")
        return []

    for yaml_path in yaml_files:
        relative_path = yaml_path.relative_to(policies_dir.parent)

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"[loader] Failed to parse {relative_path}: {e}")
            files_skipped += 1
            continue
        except OSError as e:
            logger.error(f"[loader] Failed to read {relative_path}: {e}")
            files_skipped += 1
            continue

        # Each YAML file must have a top-level 'rules' key containing a list
        if not isinstance(content, dict) or "rules" not in content:
            logger.warning(
                f"[loader] Skipping {relative_path} — "
                f"must have a top-level 'rules' list"
            )
            files_skipped += 1
            continue

        raw_rules = content.get("rules", [])
        if not isinstance(raw_rules, list):
            logger.warning(f"[loader] Skipping {relative_path} — 'rules' must be a list")
            files_skipped += 1
            continue

        file_valid = 0
        for index, rule in enumerate(raw_rules):
            if not isinstance(rule, dict):
                logger.warning(
                    f"[loader] Skipping rule at index {index} in {relative_path} — not a dict"
                )
                rules_skipped += 1
                continue

            errors = validate_rule(rule, relative_path)
            if errors:
                rules_skipped += 1
                continue

            # Enrich rule with metadata so checker.py knows where it came from
            rule["_source_file"] = str(relative_path)
            rule["_rule_index"] = index

            all_rules.append(rule)
            file_valid += 1

        files_loaded += 1
        logger.info(f"[loader] {relative_path} — {file_valid} rules loaded")

    # Final summary
    logger.info(
        f"[loader] Done — "
        f"{len(all_rules)} rules loaded from {files_loaded} files "
        f"({files_skipped} files skipped, {rules_skipped} rules skipped)"
    )

    return all_rules


# ──────────────────────────────────────────────
#  HELPERS — used by checker.py and the API
# ──────────────────────────────────────────────

def get_rules_for_service(rules, service):
    """
    Filters the full rule list to only rules matching a specific service.
    Used by checker.py to avoid running S3 rules against EC2 resources.

    Args:
        rules   : full list returned by load_policies()
        service : string e.g. "s3", "ec2", "iam"

    Returns:
        Filtered list of rules for that service.
    """
    return [r for r in rules if r.get("service") == service]


def get_rules_for_resource_type(rules, resource_type):
    """
    Filters rules by resource_type for even finer-grained matching.
    e.g. resource_type = "ec2_security_group" only runs SG rules,
    not EC2 instance rules.
    """
    return [r for r in rules if r.get("resource_type") == resource_type]


def get_rules_by_severity(rules, severity):
    """
    Returns only rules of a given severity level.
    Useful for running only CRITICAL and HIGH rules in a quick scan.
    """
    return [r for r in rules if r.get("severity") == severity]


def summarise_policies(rules):
    """
    Returns a summary dict of the loaded rule set.
    Used by the Flask API to power the Policies page in the dashboard.
    """
    from collections import Counter

    services = Counter(r.get("service") for r in rules)
    severities = Counter(r.get("severity") for r in rules)
    sources = Counter(r.get("_source_file") for r in rules)

    return {
        "total_rules": len(rules),
        "by_service": dict(services),
        "by_severity": dict(severities),
        "by_file": dict(sources),
    }


# ──────────────────────────────────────────────
#  ENTRY POINT — run directly to test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    rules = load_policies()

    print("\n" + "=" * 60)
    print(f"  LOADED {len(rules)} RULES")
    print("=" * 60)

    for rule in rules:
        severity_pad = f"[{rule['severity']:<8}]"
        print(f"  {severity_pad}  {rule['id']:<20}  {rule['title']}")

    print("\n" + "-" * 60)
    summary = summarise_policies(rules)
    print(f"\nSummary:")
    print(json.dumps(summary, indent=2))