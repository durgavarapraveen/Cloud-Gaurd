import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)

def scan_efs(session, region):
    logger.info(f"Scanning EFS in {region}...")
    client = session.client("efs", region_name=region)
    results = []
 
    fs_list = paginate(client, "describe_file_systems", "FileSystems")
    for fs in fs_list:
        fs_id = fs.get("FileSystemId")
 
        # Mount targets
        mount_targets = paginate(client, "describe_mount_targets",
                                 "MountTargets", FileSystemId=fs_id)
 
        # Access points
        access_points = paginate(client, "describe_access_points",
                                 "AccessPoints", FileSystemId=fs_id)
 
        # File system policy
        policy_resp = safe_call(client.describe_file_system_policy, FileSystemId=fs_id)
 
        # Backup policy
        backup_resp = safe_call(client.describe_backup_policy, FileSystemId=fs_id)
 
        results.append({
            "resource_type":       "efs_filesystem",
            "resource_id":         fs_id,
            "resource_name":       next((t["Value"] for t in fs.get("Tags", [])
                                         if t["Key"] == "Name"), fs_id),
            "region":              region,
            "arn":                 fs.get("FileSystemArn"),
            "lifecycle_state":     fs.get("LifeCycleState"),
            "size_bytes":          fs.get("SizeInBytes", {}).get("Value"),
            "performance_mode":    fs.get("PerformanceMode"),    # generalPurpose | maxIO
            "throughput_mode":     fs.get("ThroughputMode"),     # bursting | provisioned
            "encrypted":           fs.get("Encrypted", False),
            "kms_key_id":          fs.get("KmsKeyId"),
            "availability_zone":   fs.get("AvailabilityZoneName"),
            "number_of_mount_targets": fs.get("NumberOfMountTargets"),
            "mount_targets":       mount_targets,
            "access_points":       access_points,
            "file_system_policy":  policy_resp.get("Policy") if policy_resp else None,
            "backup_policy":       backup_resp.get("BackupPolicy", {}).get("Status") if backup_resp else None,
            "tags":                fs.get("Tags", []),
        })
 
    logger.info(f"  EFS ({region}): {len(results)} file systems")
    return results