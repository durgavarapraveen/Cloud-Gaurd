import boto3
import json
import os
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  SESSION
# ─────────────────────────────────────────────

def get_session():
    profile = os.getenv("AWS_PROFILE", "cloudguard-scanner")
    return boto3.Session(profile_name=profile)


# ─────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────

def safe_call(fn, *args, **kwargs):
    """
    Wraps any boto3 call. Returns the result or None if the call
    fails (e.g. service not enabled, permission denied for one resource).
    Prevents one failing service from crashing the whole scan.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Call failed: {fn.__name__ if hasattr(fn, '__name__') else fn} — {e}")
        return None


def paginate(client, method, result_key, **kwargs):
    """
    Handles AWS pagination automatically.
    Many AWS APIs return results in pages — this collects all pages
    into one flat list so the rest of the code never has to think about it.
    """
    try:
        paginator = client.get_paginator(method)
        results = []
        for page in paginator.paginate(**kwargs):
            results.extend(page.get(result_key, []))
        return results
    except Exception as e:
        logger.warning(f"Pagination failed for {method}: {e}")
        return []


# ─────────────────────────────────────────────
#  INDIVIDUAL SERVICE SCANNERS
# ─────────────────────────────────────────────

def scan_s3(session):
    logger.info("Scanning S3...")
    client = session.client("s3")
    buckets_resp = safe_call(client.list_buckets)
    if not buckets_resp:
        return []

    results = []
    for bucket in buckets_resp.get("Buckets", []):
        name = bucket["Name"]
        resource = {
            "resource_type": "s3_bucket",
            "resource_id": name,
            "resource_name": name,
            "region": "global",
        }

        # Encryption
        enc = safe_call(client.get_bucket_encryption, Bucket=name)
        resource["encryption"] = enc.get("ServerSideEncryptionConfiguration") if enc else None

        # Versioning
        ver = safe_call(client.get_bucket_versioning, Bucket=name)
        resource["versioning"] = ver if ver else {}

        # Public access block
        pub = safe_call(client.get_public_access_block, Bucket=name)
        resource["public_access_block"] = pub.get("PublicAccessBlockConfiguration") if pub else None

        # Logging
        log = safe_call(client.get_bucket_logging, Bucket=name)
        resource["logging"] = log.get("LoggingEnabled") if log else None

        # ACL
        acl = safe_call(client.get_bucket_acl, Bucket=name)
        resource["acl"] = acl.get("Grants") if acl else []

        # Tags
        tags_resp = safe_call(client.get_bucket_tagging, Bucket=name)
        resource["tags"] = tags_resp.get("TagSet") if tags_resp else []

        # Lifecycle
        lifecycle = safe_call(client.get_bucket_lifecycle_configuration, Bucket=name)
        resource["lifecycle"] = lifecycle.get("Rules") if lifecycle else []

        results.append(resource)

    logger.info(f"  S3: {len(results)} buckets")
    return results


def scan_ec2(session, region):
    logger.info(f"Scanning EC2 in {region}...")
    client = session.client("ec2", region_name=region)
    results = []

    # Instances
    reservations = paginate(client, "describe_instances", "Reservations")
    for reservation in reservations:
        for inst in reservation.get("Instances", []):
            resource = {
                "resource_type": "ec2_instance",
                "resource_id": inst.get("InstanceId"),
                "resource_name": next(
                    (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), 
                    inst.get("InstanceId")
                ),
                "region": region,
                "instance_type": inst.get("InstanceType"),
                "state": inst.get("State", {}).get("Name"),
                "public_ip": inst.get("PublicIpAddress"),
                "private_ip": inst.get("PrivateIpAddress"),
                "subnet_id": inst.get("SubnetId"),
                "vpc_id": inst.get("VpcId"),
                "iam_instance_profile": inst.get("IamInstanceProfile"),
                "security_groups": inst.get("SecurityGroups", []),
                "tags": inst.get("Tags", []),
                # IMDSv2 check — important CIS benchmark item
                "metadata_options": inst.get("MetadataOptions", {}),
                # EBS volumes attached
                "block_devices": inst.get("BlockDeviceMappings", []),
                "monitoring": inst.get("Monitoring", {}).get("State"),
                "launch_time": inst.get("LaunchTime").isoformat() if inst.get("LaunchTime") else None,
            }
            results.append(resource)

    # Security Groups
    sgs = paginate(client, "describe_security_groups", "SecurityGroups")
    for sg in sgs:
        resource = {
            "resource_type": "ec2_security_group",
            "resource_id": sg.get("GroupId"),
            "resource_name": sg.get("GroupName"),
            "region": region,
            "description": sg.get("Description"),
            "vpc_id": sg.get("VpcId"),
            "inbound_rules": sg.get("IpPermissions", []),
            "outbound_rules": sg.get("IpPermissionsEgress", []),
            "tags": sg.get("Tags", []),
        }
        results.append(resource)

    # EBS Volumes
    volumes = paginate(client, "describe_volumes", "Volumes")
    for vol in volumes:
        resource = {
            "resource_type": "ec2_volume",
            "resource_id": vol.get("VolumeId"),
            "resource_name": next(
                (t["Value"] for t in vol.get("Tags", []) if t["Key"] == "Name"),
                vol.get("VolumeId")
            ),
            "region": region,
            "size_gb": vol.get("Size"),
            "encrypted": vol.get("Encrypted"),
            "state": vol.get("State"),
            "volume_type": vol.get("VolumeType"),
            "attachments": vol.get("Attachments", []),
            "tags": vol.get("Tags", []),
        }
        results.append(resource)

    # VPCs
    vpcs = paginate(client, "describe_vpcs", "Vpcs")
    for vpc in vpcs:
        # Flow logs for this VPC
        flow_logs_resp = safe_call(
            client.describe_flow_logs,
            Filters=[{"Name": "resource-id", "Values": [vpc["VpcId"]]}]
        )
        resource = {
            "resource_type": "ec2_vpc",
            "resource_id": vpc.get("VpcId"),
            "resource_name": next(
                (t["Value"] for t in vpc.get("Tags", []) if t["Key"] == "Name"),
                vpc.get("VpcId")
            ),
            "region": region,
            "cidr_block": vpc.get("CidrBlock"),
            "is_default": vpc.get("IsDefault"),
            "state": vpc.get("State"),
            "flow_logs": flow_logs_resp.get("FlowLogs", []) if flow_logs_resp else [],
            "tags": vpc.get("Tags", []),
        }
        results.append(resource)

    logger.info(f"  EC2 ({region}): {len(results)} resources")
    return results


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


def scan_rds(session, region):
    logger.info(f"Scanning RDS in {region}...")
    client = session.client("rds", region_name=region)
    results = []

    # DB Instances
    instances = paginate(client, "describe_db_instances", "DBInstances")
    for db in instances:
        resource = {
            "resource_type": "rds_instance",
            "resource_id": db.get("DBInstanceIdentifier"),
            "resource_name": db.get("DBInstanceIdentifier"),
            "region": region,
            "engine": db.get("Engine"),
            "engine_version": db.get("EngineVersion"),
            "instance_class": db.get("DBInstanceClass"),
            "status": db.get("DBInstanceStatus"),
            "multi_az": db.get("MultiAZ"),
            "publicly_accessible": db.get("PubliclyAccessible"),
            "storage_encrypted": db.get("StorageEncrypted"),
            "deletion_protection": db.get("DeletionProtection"),
            "backup_retention_period": db.get("BackupRetentionPeriod"),
            "auto_minor_version_upgrade": db.get("AutoMinorVersionUpgrade"),
            "vpc_security_groups": db.get("VpcSecurityGroups", []),
            "tags": safe_call(
                client.list_tags_for_resource,
                ResourceName=db.get("DBInstanceArn")
            ) or {},
        }
        results.append(resource)

    # DB Clusters (Aurora)
    clusters = paginate(client, "describe_db_clusters", "DBClusters")
    for cluster in clusters:
        resource = {
            "resource_type": "rds_cluster",
            "resource_id": cluster.get("DBClusterIdentifier"),
            "resource_name": cluster.get("DBClusterIdentifier"),
            "region": region,
            "engine": cluster.get("Engine"),
            "status": cluster.get("Status"),
            "multi_az": cluster.get("MultiAZ"),
            "storage_encrypted": cluster.get("StorageEncrypted"),
            "deletion_protection": cluster.get("DeletionProtection"),
            "backup_retention_period": cluster.get("BackupRetentionPeriod"),
        }
        results.append(resource)

    logger.info(f"  RDS ({region}): {len(results)} resources")
    return results


def scan_cloudtrail(session, region):
    logger.info(f"Scanning CloudTrail in {region}...")
    client = session.client("cloudtrail", region_name=region)
    results = []

    trails_resp = safe_call(client.describe_trails, includeShadowTrails=False)
    for trail in (trails_resp.get("trailList", []) if trails_resp else []):
        trail_name = trail.get("TrailARN")

        status = safe_call(client.get_trail_status, Name=trail_name)
        selectors = safe_call(client.get_event_selectors, TrailName=trail_name)

        resource = {
            "resource_type": "cloudtrail_trail",
            "resource_id": trail.get("TrailARN"),
            "resource_name": trail.get("Name"),
            "region": region,
            "home_region": trail.get("HomeRegion"),
            "s3_bucket": trail.get("S3BucketName"),
            "is_multi_region": trail.get("IsMultiRegionTrail"),
            "log_file_validation": trail.get("LogFileValidationEnabled"),
            "cloudwatch_logs_arn": trail.get("CloudWatchLogsLogGroupArn"),
            "is_logging": status.get("IsLogging") if status else None,
            "event_selectors": selectors.get("EventSelectors", []) if selectors else [],
        }
        results.append(resource)

    logger.info(f"  CloudTrail ({region}): {len(results)} trails")
    return results


# ─────────────────────────────────────────────
#  MAIN COLLECTOR — runs all scanners in parallel
# ─────────────────────────────────────────────

def collect_all(regions=None):
    """
    Runs all service scanners in parallel using ThreadPoolExecutor.
    Returns a single dict with all resources grouped by service.

    Args:
        regions: list of AWS regions to scan.
                 Defaults to ['ap-south-1'] if not provided.

    Returns:
        {
            "scan_metadata": { ... },
            "resources": {
                "s3": [...],
                "ec2": [...],
                "iam": [...],
                "rds": [...],
                "cloudtrail": [...]
            },
            "summary": {
                "total_resources": 42,
                "by_service": { "s3": 3, "ec2": 15, ... }
            }
        }
    """
    if regions is None:
        regions = [os.getenv("AWS_DEFAULT_REGION", "ap-south-1")]

    session = get_session()

    # Confirm identity before scanning
    sts = session.client("sts")
    identity = safe_call(sts.get_caller_identity)
    account_id = identity.get("Account") if identity else "unknown"
    logger.info(f"Scanning account: {account_id} | regions: {regions}")

    # Build a list of (task_name, function, args) tuples
    # Each tuple becomes one parallel task
    tasks = []

    # Global services (no region needed)
    tasks.append(("s3",        scan_s3,         (session,)))
    tasks.append(("iam",       scan_iam,         (session,)))

    # Regional services — one task per region
    for region in regions:
        tasks.append((f"ec2_{region}",         scan_ec2,         (session, region)))
        tasks.append((f"rds_{region}",         scan_rds,         (session, region)))
        tasks.append((f"cloudtrail_{region}",  scan_cloudtrail,  (session, region)))

    # Run all tasks in parallel — max 10 threads
    raw_results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_name = {
            executor.submit(fn, *args): name
            for name, fn, args in tasks
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                raw_results[name] = future.result()
            except Exception as e:
                logger.error(f"Scanner {name} failed: {e}")
                raw_results[name] = []

    # Merge regional results into service buckets
    merged = {
        "s3":         raw_results.get("s3", []),
        "iam":        raw_results.get("iam", []),
        "ec2":        [],
        "rds":        [],
        "cloudtrail": [],
    }
    for region in regions:
        merged["ec2"]        += raw_results.get(f"ec2_{region}", [])
        merged["rds"]        += raw_results.get(f"rds_{region}", [])
        merged["cloudtrail"] += raw_results.get(f"cloudtrail_{region}", [])

    # Build summary counts
    by_service = {svc: len(resources) for svc, resources in merged.items()}
    total = sum(by_service.values())

    output = {
        "scan_metadata": {
            "account_id":  account_id,
            "regions":     regions,
            "scanned_at":  datetime.now(timezone.utc).isoformat(),
            "scanner":     "CloudGuard v0.1",
        },
        "resources": merged,
        "summary": {
            "total_resources": total,
            "by_service": by_service,
        },
    }

    logger.info(f"Scan complete — {total} total resources found")
    return output


# ─────────────────────────────────────────────
#  ENTRY POINT — run directly to test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    results = collect_all(regions=["ap-south-1"])

    # Pretty print the full JSON
    print(json.dumps(results, indent=2, default=str))

    # Also save to a file so you can inspect it
    output_path = "scan_output.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nSaved to {output_path}")
    print(f"\nSummary:")
    for svc, count in results["summary"]["by_service"].items():
        print(f"  {svc:15} {count} resources")
    print(f"  {'TOTAL':15} {results['summary']['total_resources']} resources")