import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)

def scan_elasticache(session, region):
    logger.info(f"Scanning ElastiCache in {region}...")
    client = session.client("elasticache", region_name=region)
    results = []
 
    # ── Replication Groups (Redis) ────────────────────────────
    rep_groups = paginate(client, "describe_replication_groups", "ReplicationGroups")
    for rg in rep_groups:
        results.append({
            "resource_type":            "elasticache_replication_group",
            "resource_id":              rg.get("ReplicationGroupId"),
            "resource_name":            rg.get("Description") or rg.get("ReplicationGroupId"),
            "region":                   region,
            "status":                   rg.get("Status"),
            "engine":                   "redis",
            "multi_az":                 rg.get("MultiAZ"),
            "automatic_failover":       rg.get("AutomaticFailover"),
            "at_rest_encryption":       rg.get("AtRestEncryptionEnabled", False),
            "in_transit_encryption":    rg.get("TransitEncryptionEnabled", False),
            "auth_token_enabled":       rg.get("AuthTokenEnabled", False),
            "cluster_mode":             rg.get("ClusterEnabled"),
            "node_groups":              len(rg.get("NodeGroups", [])),
            "snapshotting_cluster":     rg.get("SnapshottingClusterId"),
            "snapshot_retention_limit": rg.get("SnapshotRetentionLimit"),
            "arn":                      rg.get("ARN"),
        })
 
    # ── Cache Clusters (Memcached + standalone Redis) ─────────
    clusters = paginate(client, "describe_cache_clusters", "CacheClusters",
                        ShowCacheNodeInfo=True)
    for cluster in clusters:
        # Skip clusters that belong to a replication group (already captured above)
        if cluster.get("ReplicationGroupId"):
            continue
        results.append({
            "resource_type":         "elasticache_cluster",
            "resource_id":           cluster.get("CacheClusterId"),
            "resource_name":         cluster.get("CacheClusterId"),
            "region":                region,
            "status":                cluster.get("CacheClusterStatus"),
            "engine":                cluster.get("Engine"),
            "engine_version":        cluster.get("EngineVersion"),
            "node_type":             cluster.get("CacheNodeType"),
            "num_cache_nodes":       cluster.get("NumCacheNodes"),
            "at_rest_encryption":    cluster.get("AtRestEncryptionEnabled", False),
            "in_transit_encryption": cluster.get("TransitEncryptionEnabled", False),
            "multi_az":              cluster.get("PreferredAvailabilityZone") == "Multiple",
            "auto_minor_upgrade":    cluster.get("AutoMinorVersionUpgrade"),
            "subnet_group":          cluster.get("CacheSubnetGroupName"),
            "security_groups":       cluster.get("SecurityGroups", []),
            "arn":                   cluster.get("ARN"),
        })
 
    logger.info(f"  ElastiCache ({region}): {len(results)} resources")
    return results