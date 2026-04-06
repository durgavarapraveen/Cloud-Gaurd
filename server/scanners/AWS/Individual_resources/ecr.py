import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)

def scan_ecr(session, region):
    logger.info(f"Scanning ECR in {region}...")
    client = session.client("ecr", region_name=region)
    results = []
 
    repos = paginate(client, "describe_repositories", "repositories")
    for repo in repos:
        repo_name = repo.get("repositoryName")
        repo_arn  = repo.get("repositoryArn")
 
        # Scan config — is image scanning on push enabled?
        scan_config = repo.get("imageScanningConfiguration", {})
 
        # Lifecycle policy
        lifecycle = safe_call(client.get_lifecycle_policy, repositoryName=repo_name)
 
        # Repository policy (who can pull/push)
        repo_policy = safe_call(client.get_repository_policy, repositoryName=repo_name)
 
        # Image tag mutability
        tag_mutability = repo.get("imageTagMutability", "MUTABLE")
 
        # Tags
        tags_resp = safe_call(client.list_tags_for_resource, resourceArn=repo_arn)
 
        results.append({
            "resource_type":       "ecr_repository",
            "resource_id":         repo_arn,
            "resource_name":       repo_name,
            "region":              region,
            "repository_uri":      repo.get("repositoryUri"),
            "created_at":          repo.get("createdAt").isoformat() if repo.get("createdAt") else None,
            "image_tag_mutability": tag_mutability,          # MUTABLE | IMMUTABLE
            "scan_on_push":        scan_config.get("scanOnPush", False),
            "encryption_type":     repo.get("encryptionConfiguration", {}).get("encryptionType"),
            "kms_key":             repo.get("encryptionConfiguration", {}).get("kmsKey"),
            "lifecycle_policy":    lifecycle.get("lifecyclePolicyText") if lifecycle else None,
            "repository_policy":   repo_policy.get("policyText") if repo_policy else None,
            "tags":                tags_resp.get("tags", []) if tags_resp else [],
        })
 
    logger.info(f"  ECR ({region}): {len(results)} repositories")
    return results