import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)


def scan_privatelink(session, region):
    logger.info(f"Scanning PrivateLink/VPC Endpoints in {region}...")
    client = session.client("ec2", region_name=region)
    results = []
 
    # ── VPC Endpoints (Interface + Gateway) ──────────────────
    endpoints = paginate(client, "describe_vpc_endpoints", "VpcEndpoints")
    for ep in endpoints:
        results.append({
            "resource_type":     "vpc_endpoint",
            "resource_id":       ep.get("VpcEndpointId"),
            "resource_name":     next((t["Value"] for t in ep.get("Tags", [])
                                        if t["Key"] == "Name"), ep.get("VpcEndpointId")),
            "region":            region,
            "vpc_id":            ep.get("VpcId"),
            "service_name":      ep.get("ServiceName"),
            "endpoint_type":     ep.get("VpcEndpointType"),   # Interface | Gateway | GatewayLoadBalancer
            "state":             ep.get("State"),
            "private_dns":       ep.get("PrivateDnsEnabled"),
            "subnet_ids":        ep.get("SubnetIds", []),
            "security_groups":   [sg.get("GroupId") for sg in ep.get("Groups", [])],
            "route_table_ids":   ep.get("RouteTableIds", []),
            "dns_entries":       ep.get("DnsEntries", []),
            "creation_timestamp": ep.get("CreationTimestamp").isoformat()
                                   if ep.get("CreationTimestamp") else None,
            "tags":              ep.get("Tags", []),
        })
 
    # ── Endpoint Services (services you publish) ─────────────
    svc_resp = safe_call(client.describe_vpc_endpoint_services,
                         Filters=[{"Name": "owner", "Values": ["self"]}])
    for svc in (svc_resp.get("ServiceDetails", []) if svc_resp else []):
        results.append({
            "resource_type":      "vpc_endpoint_service",
            "resource_id":        svc.get("ServiceId"),
            "resource_name":      svc.get("ServiceName"),
            "region":             region,
            "service_type":       [t.get("ServiceType") for t in svc.get("ServiceType", [])],
            "acceptance_required": svc.get("AcceptanceRequired"),
            "manages_vpc_endpoints": svc.get("ManagesVpcEndpoints"),
            "availability_zones": svc.get("AvailabilityZones", []),
            "tags":               svc.get("Tags", []),
        })
 
    logger.info(f"  PrivateLink ({region}): {len(results)} resources")
    return results