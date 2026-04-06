import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)

def scan_route53(session):
    logger.info("Scanning Route 53 (global)...")
    client = session.client("route53")
    results = []
 
    # ── Hosted Zones ─────────────────────────
    zones_resp = safe_call(client.list_hosted_zones)
    for zone in (zones_resp.get("HostedZones", []) if zones_resp else []):
        zone_id = zone.get("Id", "").split("/")[-1]  # strip /hostedzone/ prefix
 
        # Query logging config
        logging_resp = safe_call(client.list_query_logging_configs,
                                 HostedZoneId=zone_id)
 
        # DNSSEC status
        dnssec_resp = safe_call(client.get_dnssec, HostedZoneId=zone_id)
 
        # Tags on hosted zones use a different API
        tags_resp = safe_call(client.list_tags_for_resource,
                              ResourceType="hostedzone", ResourceId=zone_id)
 
        results.append({
            "resource_type":    "route53_hosted_zone",
            "resource_id":      zone_id,
            "resource_name":    zone.get("Name"),
            "region":           "global",
            "private_zone":     zone.get("Config", {}).get("PrivateZone", False),
            "record_count":     zone.get("ResourceRecordSetCount"),
            "comment":          zone.get("Config", {}).get("Comment"),
            "query_logging":    bool(logging_resp.get("QueryLoggingConfigs")) if logging_resp else False,
            "dnssec_status":    dnssec_resp.get("Status", {}).get("ServeSignature") if dnssec_resp else None,
            "tags":             tags_resp.get("ResourceTagSet", {}).get("Tags", []) if tags_resp else [],
        })
 
    # ── Health Checks ────────────────────────
    health_checks_resp = safe_call(client.list_health_checks)
    for hc in (health_checks_resp.get("HealthChecks", []) if health_checks_resp else []):
        config = hc.get("HealthCheckConfig", {})
        results.append({
            "resource_type":    "route53_health_check",
            "resource_id":      hc.get("Id"),
            "resource_name":    hc.get("Id"),
            "region":           "global",
            "type":             config.get("Type"),
            "endpoint":         config.get("FullyQualifiedDomainName") or config.get("IPAddress"),
            "port":             config.get("Port"),
            "protocol":         config.get("Type"),
            "request_interval": config.get("RequestInterval"),
            "failure_threshold": config.get("FailureThreshold"),
        })
 
    logger.info(f"  Route 53 (global): {len(results)} resources")
    return results