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