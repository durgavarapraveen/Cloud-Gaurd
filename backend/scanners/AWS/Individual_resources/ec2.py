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