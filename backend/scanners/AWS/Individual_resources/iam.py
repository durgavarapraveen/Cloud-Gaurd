import boto3
import json
import os
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from utils import safe_call, paginate

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def scan_iam(session):
    logger.info("Scanning IAM...")
    client = session.client("iam")
    results = []

    # Account password policy
    pwd_policy = safe_call(client.get_account_password_policy)
    if pwd_policy:
        results.append({
            "resource_type": "iam_password_policy",
            "resource_id": "account-password-policy",
            "resource_name": "Account Password Policy",
            "region": "global",
            **pwd_policy.get("PasswordPolicy", {}),
        })

    # Account summary (root account checks)
    summary = safe_call(client.get_account_summary)
    if summary:
        results.append({
            "resource_type": "iam_account_summary",
            "resource_id": "account-summary",
            "resource_name": "Account Summary",
            "region": "global",
            "summary_map": summary.get("SummaryMap", {}),
        })

    # IAM Users
    users = paginate(client, "list_users", "Users")
    for user in users:
        username = user["UserName"]

        # MFA devices
        mfa = safe_call(client.list_mfa_devices, UserName=username)
        # Access keys
        keys = safe_call(client.list_access_keys, UserName=username)
        # Attached policies
        attached = safe_call(client.list_attached_user_policies, UserName=username)
        # Inline policies
        inline = safe_call(client.list_user_policies, UserName=username)

        resource = {
            "resource_type": "iam_user",
            "resource_id": user.get("UserId"),
            "resource_name": username,
            "region": "global",
            "arn": user.get("Arn"),
            "created": user.get("CreateDate").isoformat() if user.get("CreateDate") else None,
            "password_last_used": user.get("PasswordLastUsed").isoformat() if user.get("PasswordLastUsed") else None,
            "mfa_devices": mfa.get("MFADevices", []) if mfa else [],
            "access_keys": [
                {
                    "access_key_id": k.get("AccessKeyId"),
                    "status": k.get("Status"),
                    "created": k.get("CreateDate").isoformat() if k.get("CreateDate") else None,
                }
                for k in (keys.get("AccessKeyMetadata", []) if keys else [])
            ],
            "attached_policies": attached.get("AttachedPolicies", []) if attached else [],
            "inline_policies": inline.get("PolicyNames", []) if inline else [],
        }
        results.append(resource)

    # IAM Roles
    roles = paginate(client, "list_roles", "Roles")
    for role in roles:
        resource = {
            "resource_type": "iam_role",
            "resource_id": role.get("RoleId"),
            "resource_name": role.get("RoleName"),
            "region": "global",
            "arn": role.get("Arn"),
            "created": role.get("CreateDate").isoformat() if role.get("CreateDate") else None,
            "trust_policy": role.get("AssumeRolePolicyDocument", {}),
            "description": role.get("Description"),
            "tags": role.get("Tags", []),
        }
        results.append(resource)

    logger.info(f"  IAM: {len(results)} resources")
    return results