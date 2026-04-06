import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)

def scan_ebs(session, region):
    logger.info(f"Scanning EBS (snapshots + account config) in {region}...")
    client = session.client("ec2", region_name=region)
    results = []
 
    # ── Account-level EBS encryption default ─────────────────
    enc_resp = safe_call(client.get_ebs_encryption_by_default)
    if enc_resp:
        results.append({
            "resource_type":        "ebs_account_encryption",
            "resource_id":          f"ebs-encryption-default-{region}",
            "resource_name":        f"EBS Default Encryption ({region})",
            "region":               region,
            "encryption_by_default": enc_resp.get("EbsEncryptionByDefault", False),
            "kms_key_id":           enc_resp.get("KmsKeyId"),
        })
 
    # ── Snapshots owned by this account ──────────────────────
    snapshots = paginate(client, "describe_snapshots", "Snapshots",
                         OwnerIds=["self"])
    for snap in snapshots:
        results.append({
            "resource_type":   "ebs_snapshot",
            "resource_id":     snap.get("SnapshotId"),
            "resource_name":   next((t["Value"] for t in snap.get("Tags", [])
                                     if t["Key"] == "Name"), snap.get("SnapshotId")),
            "region":          region,
            "volume_id":       snap.get("VolumeId"),
            "volume_size_gb":  snap.get("VolumeSize"),
            "state":           snap.get("State"),
            "encrypted":       snap.get("Encrypted", False),
            "kms_key_id":      snap.get("KmsKeyId"),
            "start_time":      snap.get("StartTime").isoformat() if snap.get("StartTime") else None,
            "description":     snap.get("Description"),
            "owner_id":        snap.get("OwnerId"),
            "tags":            snap.get("Tags", []),
        })
 
    logger.info(f"  EBS ({region}): 1 account config + {len(results)-1} snapshots")
    return results
 