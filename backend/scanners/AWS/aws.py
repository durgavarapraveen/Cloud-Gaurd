import boto3, os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

profile = os.getenv('AWS_PROFILE', 'cloudguard-scanner')
session = boto3.Session(profile_name=profile)

client = boto3.client('resource-explorer-2')

response = client.search(
    QueryString="*"
)

for resource in response['Resources']:
    print(resource['Arn'])
    print(resource['Region'])
    print(resource['ResourceType'])
    print("------")