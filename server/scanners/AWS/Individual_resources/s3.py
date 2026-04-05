import logging

from scanners.AWS.utils import safe_call

logger = logging.getLogger(__name__)


def scan_s3(session):

    logger.info("Scanning S3")

    client = session.client("s3")

    buckets_resp = safe_call(
        client.list_buckets
    )

    if not buckets_resp:

        return []

    results = []

    for bucket in buckets_resp.get("Buckets", []):

        name = bucket["Name"]

        # Bucket region
        location = safe_call(
            client.get_bucket_location,
            Bucket=name
        )

        region = "us-east-1"

        if location:
            region = location.get(
                "LocationConstraint"
            ) or "us-east-1"

        # Encryption

        enc = safe_call(
            client.get_bucket_encryption,
            Bucket=name
        )

        encryption = None

        if enc:
            encryption = enc.get(
                "ServerSideEncryptionConfiguration"
            )

        # Versioning

        ver = safe_call(
            client.get_bucket_versioning,
            Bucket=name
        ) or {}

        # Public access block

        pub = safe_call(
            client.get_public_access_block,
            Bucket=name
        )

        public_block = None

        if pub:
            public_block = pub.get(
                "PublicAccessBlockConfiguration"
            )

        # Logging

        log = safe_call(
            client.get_bucket_logging,
            Bucket=name
        )

        logging_cfg = None

        if log:
            logging_cfg = log.get(
                "LoggingEnabled"
            )

        # ACL

        acl = safe_call(
            client.get_bucket_acl,
            Bucket=name
        )

        grants = []

        if acl:
            grants = acl.get(
                "Grants",
                []
            )

        # Tags

        tags_resp = safe_call(
            client.get_bucket_tagging,
            Bucket=name
        )

        tags = []

        if tags_resp:
            tags = tags_resp.get(
                "TagSet",
                []
            )

        # Lifecycle

        lifecycle = safe_call(
            client.get_bucket_lifecycle_configuration,
            Bucket=name
        )

        lifecycle_rules = []

        if lifecycle:
            lifecycle_rules = lifecycle.get(
                "Rules",
                []
            )

        resource = {

            "service": "s3",

            "resource_type": "s3_bucket",

            "resource_id": name,

            "resource_name": name,

            "arn":
                f"arn:aws:s3:::{name}",

            "region": region,

            "created":
                bucket.get("CreationDate"),

            "configuration": {

                "encryption": encryption,

                "versioning": ver,

                "public_access_block":
                    public_block,

                "logging":
                    logging_cfg,

                "acl":
                    grants,

                "lifecycle":
                    lifecycle_rules
            },

            "tags": tags
        }

        results.append(resource)

    logger.info(f"S3 → {len(results)} buckets")

    return results