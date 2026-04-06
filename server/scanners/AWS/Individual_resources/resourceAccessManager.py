import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)

def scan_ram(session, region):
    logger.info(f"Scanning RAM in {region}...")
    client = session.client("ram", region_name=region)
    results = []
 
    # ── Resource Shares owned by this account ────────────────
    own_shares = paginate(client, "get_resource_shares", "resourceShares",
                          resourceOwner="SELF")
    for share in own_shares:
        share_arn = share.get("resourceShareArn")
 
        # Resources in this share
        resources = paginate(client, "list_resources", "resources",
                             resourceOwner="SELF",
                             resourceShareArns=[share_arn])
 
        # Principals this share is shared with
        principals = paginate(client, "list_principals", "principals",
                              resourceOwner="SELF",
                              resourceShareArns=[share_arn])
 
        results.append({
            "resource_type":         "ram_resource_share",
            "resource_id":           share_arn,
            "resource_name":         share.get("name"),
            "region":                region,
            "status":                share.get("status"),
            "allow_external_principals": share.get("allowExternalPrincipals", False),
            "owning_account_id":     share.get("owningAccountId"),
            "feature_set":           share.get("featureSet"),
            "creation_time":         share.get("creationTime").isoformat()
                                      if share.get("creationTime") else None,
            "last_updated":          share.get("lastUpdatedTime").isoformat()
                                      if share.get("lastUpdatedTime") else None,
            "resources":             [r.get("arn") for r in resources],
            "principals":            [p.get("id") for p in principals],
            "tags":                  share.get("tags", []),
        })
 
    # ── Resource Shares shared WITH this account ─────────────
    ext_shares = paginate(client, "get_resource_shares", "resourceShares",
                          resourceOwner="OTHER-ACCOUNTS")
    for share in ext_shares:
        results.append({
            "resource_type":     "ram_shared_with_me",
            "resource_id":       share.get("resourceShareArn"),
            "resource_name":     share.get("name"),
            "region":            region,
            "status":            share.get("status"),
            "owning_account_id": share.get("owningAccountId"),
            "feature_set":       share.get("featureSet"),
        })
 
    logger.info(f"  RAM ({region}): {len(results)} resource shares")
    return results