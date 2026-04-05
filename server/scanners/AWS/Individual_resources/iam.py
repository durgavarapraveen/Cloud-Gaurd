import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)


def scan_iam(session):

    logger.info("Scanning IAM")

    client = session.client("iam")

    results = []

    # ─────────────────────────────
    # PASSWORD POLICY
    # ─────────────────────────────

    pwd_policy = safe_call(
        client.get_account_password_policy
    )

    if pwd_policy:

        results.append({

            "service": "iam",

            "resource_type":
                "iam_password_policy",

            "resource_id":
                "account-password-policy",

            "resource_name":
                "Account Password Policy",

            "region": "global",

            "configuration":
                pwd_policy.get(
                    "PasswordPolicy",
                    {}
                ),

            "tags": []
        })

    # ─────────────────────────────
    # ACCOUNT SUMMARY
    # ─────────────────────────────

    summary = safe_call(
        client.get_account_summary
    )

    if summary:

        results.append({

            "service": "iam",

            "resource_type":
                "iam_account_summary",

            "resource_id":
                "account-summary",

            "resource_name":
                "Account Summary",

            "region": "global",

            "configuration": {

                "summary_map":
                    summary.get(
                        "SummaryMap",
                        {}
                    )
            },

            "tags":[]
        })

    # ─────────────────────────────
    # USERS
    # ─────────────────────────────

    users = paginate(
        client,
        "list_users",
        "Users"
    )

    for user in users:

        username = user["UserName"]

        mfa = safe_call(
            client.list_mfa_devices,
            UserName=username
        )

        keys = safe_call(
            client.list_access_keys,
            UserName=username
        )

        attached = safe_call(
            client.list_attached_user_policies,
            UserName=username
        )

        inline = safe_call(
            client.list_user_policies,
            UserName=username
        )

        resource = {

            "service": "iam",

            "resource_type":
                "iam_user",

            "resource_id":
                user.get("UserId"),

            "resource_name":
                username,

            "arn":
                user.get("Arn"),

            "region":
                "global",

            "created":
                user.get("CreateDate").isoformat()
                if user.get("CreateDate")
                else None,

            "configuration": {

                "password_last_used":
                    user.get("PasswordLastUsed").isoformat()
                    if user.get("PasswordLastUsed")
                    else None,

                "mfa_devices":
                    mfa.get("MFADevices", [])
                    if mfa else [],

                "mfa_enabled":
                    True if mfa and
                    len(mfa.get(
                        "MFADevices",
                        []
                    )) > 0 else False,

                "access_keys":[

                    {

                        "access_key_id":
                            k.get("AccessKeyId"),

                        "status":
                            k.get("Status"),

                        "created":
                            k.get("CreateDate").isoformat()
                            if k.get("CreateDate")
                            else None
                    }

                    for k in (
                        keys.get(
                            "AccessKeyMetadata",
                            []
                        ) if keys else []
                    )
                ],

                "attached_policies":
                    attached.get(
                        "AttachedPolicies",
                        []
                    ) if attached else [],

                "inline_policies":
                    inline.get(
                        "PolicyNames",
                        []
                    ) if inline else []
            },

            "tags":[]
        }

        results.append(resource)

    # ─────────────────────────────
    # ROLES
    # ─────────────────────────────

    roles = paginate(
        client,
        "list_roles",
        "Roles"
    )

    for role in roles:

        resource = {

            "service": "iam",

            "resource_type":
                "iam_role",

            "resource_id":
                role.get("RoleId"),

            "resource_name":
                role.get("RoleName"),

            "arn":
                role.get("Arn"),

            "region":
                "global",

            "created":
                role.get("CreateDate").isoformat()
                if role.get("CreateDate")
                else None,

            "configuration": {

                "trust_policy":
                    role.get(
                        "AssumeRolePolicyDocument",
                        {}
                    ),

                "description":
                    role.get("Description")
            },

            "tags":
                role.get(
                    "Tags",
                    []
                )
        }

        results.append(resource)

    logger.info(f"IAM → {len(results)} resources")

    return results