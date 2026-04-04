import boto3
import json
import os
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from utils import safe_call

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)



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