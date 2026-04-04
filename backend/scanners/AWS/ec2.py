import boto3
import json

ec2 = boto3.client('ec2')

def get_ec2_inventory():

    paginator = ec2.get_paginator('describe_instances')

    instances_data = []

    for page in paginator.paginate():

        for reservation in page['Reservations']:

            for instance in reservation['Instances']:

                instance_info = {

                    "InstanceId":
                    instance.get("InstanceId"),

                    "InstanceType":
                    instance.get("InstanceType"),

                    "State":
                    instance.get("State",{}).get("Name"),

                    "LaunchTime":
                    str(instance.get("LaunchTime")),

                    "AMI":
                    instance.get("ImageId"),

                    "KeyName":
                    instance.get("KeyName"),

                    "VPC":
                    instance.get("VpcId"),

                    "Subnet":
                    instance.get("SubnetId"),

                    "PrivateIP":
                    instance.get("PrivateIpAddress"),

                    "PublicIP":
                    instance.get("PublicIpAddress"),

                    "SecurityGroups":
                    instance.get("SecurityGroups"),

                    "IAMRole":
                    instance.get("IamInstanceProfile"),

                    "Monitoring":
                    instance.get("Monitoring",{}).get("State"),

                    "Platform":
                    instance.get("PlatformDetails"),

                    "Architecture":
                    instance.get("Architecture"),

                    "CPUOptions":
                    instance.get("CpuOptions"),

                    "BlockDevices":
                    instance.get("BlockDeviceMappings"),

                    "NetworkInterfaces":
                    instance.get("NetworkInterfaces"),

                    "Tags":
                    instance.get("Tags"),

                    "MetadataOptions":
                    instance.get("MetadataOptions")
                }

                instances_data.append(instance_info)

    print(json.dumps(instances_data, indent=2, default=str))


get_ec2_inventory()