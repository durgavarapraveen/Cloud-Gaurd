import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)

def scan_kms(session, region):
    logger.info(f"Scanning KMS in {region}...")
    client = session.client("kms", region_name=region)
    results = []
 
    keys = paginate(client, "list_keys", "Keys")
    for key in keys:
        key_id = key.get("KeyId")
 
        # Full key metadata
        meta_resp = safe_call(client.describe_key, KeyId=key_id)
        if not meta_resp:
            continue
        meta = meta_resp.get("KeyMetadata", {})
 
        # Skip AWS-managed keys (aws/...) — only report customer keys
        if meta.get("KeyManager") == "AWS":
            continue
 
        # Key policy
        policy_resp = safe_call(client.get_key_policy, KeyId=key_id, PolicyName="default")
 
        # Key rotation status
        rotation_resp = safe_call(client.get_key_rotation_status, KeyId=key_id)
 
        # Tags
        tags_resp = safe_call(client.list_resource_tags, KeyId=key_id)
 
        results.append({
            "resource_type":       "kms_key",
            "resource_id":         meta.get("KeyId"),
            "resource_name":       meta.get("Description") or meta.get("KeyId"),
            "region":              region,
            "arn":                 meta.get("Arn"),
            "key_state":           meta.get("KeyState"),         # Enabled | Disabled | PendingDeletion
            "key_usage":           meta.get("KeyUsage"),         # ENCRYPT_DECRYPT | SIGN_VERIFY
            "key_spec":            meta.get("KeySpec"),          # SYMMETRIC_DEFAULT | RSA_* | ECC_*
            "key_manager":         meta.get("KeyManager"),       # CUSTOMER | AWS
            "origin":              meta.get("Origin"),           # AWS_KMS | EXTERNAL | AWS_CLOUDHSM
            "multi_region":        meta.get("MultiRegion", False),
            "rotation_enabled":    rotation_resp.get("KeyRotationEnabled") if rotation_resp else None,
            "deletion_date":       meta.get("DeletionDate").isoformat() if meta.get("DeletionDate") else None,
            "creation_date":       meta.get("CreationDate").isoformat() if meta.get("CreationDate") else None,
            "key_policy":          policy_resp.get("Policy") if policy_resp else None,
            "tags":                tags_resp.get("Tags", []) if tags_resp else [],
        })
 
    logger.info(f"  KMS ({region}): {len(results)} customer-managed keys")
    return results