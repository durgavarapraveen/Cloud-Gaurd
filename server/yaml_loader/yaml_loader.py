import yaml
from bson import ObjectId
from db.db import db

async def store_yaml(provider: str, service: str, yaml_content: str):
    """
    Store YAML as JSON document in MongoDB
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML content: {str(e)}")

    document = {
        "provider": provider,
        "service": service,
        "data": data,
    }
    
    # check if a document with the same provider and service already exists
    existing_doc = await db["resources"].find_one({"provider": provider, "service": service})
    if existing_doc:
        # update the existing document
        await db["resources"].update_one(
            {"_id": existing_doc["_id"]},
            {"$set": {"data": data}}
        )
        return str(existing_doc["_id"])

    result = await db["resources"].insert_one(document)
    return str(result.inserted_id)


async def get_policies(provider: str = None, service: str = None):
    query = {}
    if provider:
        query["provider"] = provider
    if service:
        query["service"] = service

    cursor = db["resources"].find(query)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results

async def get_policy_by_provider(provider: str = None):
    query = {}
    if provider:
        query["provider"] = provider

    cursor = db["resources"].find(query)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results

async def delete_policy(document_id: str):
    result = await db["resources"].delete_one({"_id": ObjectId(document_id)})
    return result.deleted_count > 0