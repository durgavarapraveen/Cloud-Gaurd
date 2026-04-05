import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)


def scan_ec2(session, region):

    logger.info(f"Scanning EC2 in {region}")

    client = session.client(
        "ec2",
        region_name=region
    )

    results = []

    # ─────────────────────────────
    # INSTANCES
    # ─────────────────────────────

    reservations = paginate(
        client,
        "describe_instances",
        "Reservations"
    )

    for reservation in reservations:

        for inst in reservation.get(
            "Instances",
            []
        ):

            name = next(

                (t["Value"]
                 for t in inst.get("Tags", [])
                 if t["Key"] == "Name"),

                inst.get("InstanceId")
            )

            resource = {

                "service": "ec2",

                "resource_type":
                    "ec2_instance",

                "resource_id":
                    inst.get("InstanceId"),

                "resource_name":
                    name,

                "arn":
                    f"arn:aws:ec2:{region}::instance/{inst.get('InstanceId')}",

                "region": region,

                "configuration": {

                    "instance_type":
                        inst.get("InstanceType"),

                    "state":
                        inst.get("State", {}).get("Name"),

                    "public_ip":
                        inst.get("PublicIpAddress"),

                    "private_ip":
                        inst.get("PrivateIpAddress"),

                    "subnet_id":
                        inst.get("SubnetId"),

                    "vpc_id":
                        inst.get("VpcId"),

                    "iam_instance_profile":
                        inst.get("IamInstanceProfile"),

                    "security_groups":
                        inst.get("SecurityGroups", []),

                    "metadata_options":
                        inst.get("MetadataOptions", {}),

                    "block_devices":
                        inst.get("BlockDeviceMappings", []),

                    "monitoring":
                        inst.get("Monitoring", {}).get("State"),

                    "launch_time":
                        inst.get("LaunchTime").isoformat() if inst.get("LaunchTime") else None,

                    "imdsv2": 
                        inst.get("MetadataOptions", {}).get("HttpTokens") == "required"
                        
                },

                "tags":
                    inst.get("Tags", [])
            }

            results.append(resource)

    # ─────────────────────────────
    # SECURITY GROUPS
    # ─────────────────────────────

    sgs = paginate(
        client,
        "describe_security_groups",
        "SecurityGroups"
    )

    for sg in sgs:

        resource = {

            "service": "ec2",

            "resource_type":
                "ec2_security_group",

            "resource_id":
                sg.get("GroupId"),

            "resource_name":
                sg.get("GroupName"),

            "arn":
                f"arn:aws:ec2:{region}::security-group/{sg.get('GroupId')}",

            "region": region,

            "configuration": {

                "description":
                    sg.get("Description"),

                "vpc_id":
                    sg.get("VpcId"),

                "inbound_rules":
                    sg.get("IpPermissions", []),

                "outbound_rules":
                    sg.get("IpPermissionsEgress", [])
            },

            "tags":
                sg.get("Tags", [])
        }

        results.append(resource)

    # ─────────────────────────────
    # EBS VOLUMES
    # ─────────────────────────────

    volumes = paginate(
        client,
        "describe_volumes",
        "Volumes"
    )

    for vol in volumes:

        name = next(

            (t["Value"]
             for t in vol.get("Tags", [])
             if t["Key"] == "Name"),

            vol.get("VolumeId")
        )

        resource = {

            "service": "ec2",

            "resource_type":
                "ec2_volume",

            "resource_id":
                vol.get("VolumeId"),

            "resource_name":
                name,

            "arn":
                f"arn:aws:ec2:{region}::volume/{vol.get('VolumeId')}",

            "region": region,

            "configuration": {

                "size_gb":
                    vol.get("Size"),

                "encrypted":
                    vol.get("Encrypted"),

                "state":
                    vol.get("State"),

                "volume_type":
                    vol.get("VolumeType"),

                "attachments":
                    vol.get("Attachments", [])
            },

            "tags":
                vol.get("Tags", [])
        }

        results.append(resource)

    # ─────────────────────────────
    # VPCS
    # ─────────────────────────────

    vpcs = paginate(
        client,
        "describe_vpcs",
        "Vpcs"
    )

    for vpc in vpcs:

        flow_logs = safe_call(

            client.describe_flow_logs,

            Filters=[
                {
                    "Name":
                    "resource-id",

                    "Values":
                    [vpc["VpcId"]]
                }
            ]
        )

        name = next(

            (t["Value"]
             for t in vpc.get("Tags", [])
             if t["Key"] == "Name"),

            vpc.get("VpcId")
        )

        resource = {

            "service": "ec2",

            "resource_type":
                "ec2_vpc",

            "resource_id":
                vpc.get("VpcId"),

            "resource_name":
                name,

            "arn":
                f"arn:aws:ec2:{region}::vpc/{vpc.get('VpcId')}",

            "region": region,

            "configuration": {

                "cidr_block":
                    vpc.get("CidrBlock"),

                "is_default":
                    vpc.get("IsDefault"),

                "state":
                    vpc.get("State"),

                "flow_logs":
                    flow_logs.get("FlowLogs", [])
                    if flow_logs else []
            },

            "tags":
                vpc.get("Tags", [])
        }

        results.append(resource)

    logger.info(f"EC2 {region} → {len(results)} resources")

    return results