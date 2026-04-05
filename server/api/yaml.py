from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from yaml_loader.yaml_loader import (
    store_yaml,
    get_policies,
    get_policy_by_provider,
    delete_policy,
    get_policy_by_id,
    edit_policy_by_id
)

router = APIRouter(
    prefix="/yaml",
    tags=["YAML Loader"]
)

class YAMLUploadRequest(BaseModel):
    provider: str
    service: str
    yaml_content: str

@router.post("/upload")
async def upload_yaml(request: YAMLUploadRequest):
    try:
        document_id = await store_yaml(request.provider, request.service, request.yaml_content)
        return {"message": "YAML content stored successfully", "id": document_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.get("/policies")
async def get_yaml_policies(provider: str = None, service: str = None):
    resources = await get_policies(provider.lower() if provider else None, service)
    return {"resources": resources}

@router.get("/policies/{provider}")
async def get_yaml_policies_by_provider(provider: str):
    resources = await get_policy_by_provider(provider.lower())
    return {"resources": resources}

@router.delete("/policies/{document_id}")
async def delete_yaml_policy(document_id: str):
    try:
        await delete_policy(document_id)
        return {"message": "Policy deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/policy/{document_id}")
async def get_yaml_policy(document_id: str):
    try:
        policy = await get_policy_by_id(document_id)
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        return {"policy": policy}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/policy/{document_id}")
async def edit_yaml_policy(document_id: str, request: YAMLUploadRequest):
    try:
        updated_id = await edit_policy_by_id(document_id, request.provider, request.service, request.yaml_content)
        return {"message": "Policy updated successfully", "id": updated_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))