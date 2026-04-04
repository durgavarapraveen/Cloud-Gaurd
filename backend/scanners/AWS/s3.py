import boto3
import json
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

def safe_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ClientError as e:
        return {"Error": str(e)}

def get_bucket_region(bucket):
    try:
        location = s3.get_bucket_location(Bucket=bucket)
        return location['LocationConstraint'] or 'us-east-1'
    except:
        return "unknown"

def get_s3_inventory():

    buckets = s3.list_buckets()

    full_inventory = []

    for bucket in buckets['Buckets']:

        name = bucket['Name']

        print(f"Scanning {name}")

        bucket_data = {
            "Name": name,
            "CreationDate": str(bucket['CreationDate']),
            "Region": get_bucket_region(name),

            "Versioning":
            safe_call(s3.get_bucket_versioning, Bucket=name),

            "Encryption":
            safe_call(s3.get_bucket_encryption, Bucket=name),

            "Policy":
            safe_call(s3.get_bucket_policy, Bucket=name),

            "ACL":
            safe_call(s3.get_bucket_acl, Bucket=name),

            "PublicAccessBlock":
            safe_call(s3.get_public_access_block, Bucket=name),

            "Logging":
            safe_call(s3.get_bucket_logging, Bucket=name),

            "Lifecycle":
            safe_call(s3.get_bucket_lifecycle_configuration,
            Bucket=name),

            "Replication":
            safe_call(s3.get_bucket_replication, Bucket=name),

            "Tags":
            safe_call(s3.get_bucket_tagging, Bucket=name),

            "CORS":
            safe_call(s3.get_bucket_cors, Bucket=name),

            "Website":
            safe_call(s3.get_bucket_website, Bucket=name),

            "ObjectLock":
            safe_call(s3.get_object_lock_configuration,
            Bucket=name)
        }

        full_inventory.append(bucket_data)

    print(json.dumps(full_inventory, indent=2, default=str))


get_s3_inventory()