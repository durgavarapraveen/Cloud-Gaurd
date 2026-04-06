import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)


def scan_transit_gateway(session, region):
    logger.info(f"Scanning Transit Gateway in {region}...")
    client = session.client("ec2", region_name=region)
    results = []
 
    # ── Transit Gateways ─────────────────────
    tgws = paginate(client, "describe_transit_gateways", "TransitGateways")
    for tgw in tgws:
        tgw_id = tgw.get("TransitGatewayId")
        options = tgw.get("Options", {})
 
        results.append({
            "resource_type":            "transit_gateway",
            "resource_id":              tgw_id,
            "resource_name":            next((t["Value"] for t in tgw.get("Tags", [])
                                              if t["Key"] == "Name"), tgw_id),
            "region":                   region,
            "arn":                      tgw.get("TransitGatewayArn"),
            "owner_id":                 tgw.get("OwnerId"),
            "state":                    tgw.get("State"),
            "amazon_side_asn":          options.get("AmazonSideAsn"),
            "auto_accept_attachments":  options.get("AutoAcceptSharedAttachments"),
            "default_route_table_association": options.get("DefaultRouteTableAssociation"),
            "default_route_table_propagation": options.get("DefaultRouteTablePropagation"),
            "vpn_ecmp_support":         options.get("VpnEcmpSupport"),
            "dns_support":              options.get("DnsSupport"),
            "multicast_support":        options.get("MulticastSupport"),
            "creation_time":            tgw.get("CreationTime").isoformat()
                                         if tgw.get("CreationTime") else None,
            "tags":                     tgw.get("Tags", []),
        })
 
    # ── TGW Attachments ──────────────────────
    attachments = paginate(client, "describe_transit_gateway_attachments",
                           "TransitGatewayAttachments")
    for att in attachments:
        results.append({
            "resource_type":        "transit_gateway_attachment",
            "resource_id":          att.get("TransitGatewayAttachmentId"),
            "resource_name":        next((t["Value"] for t in att.get("Tags", [])
                                          if t["Key"] == "Name"),
                                         att.get("TransitGatewayAttachmentId")),
            "region":               region,
            "transit_gateway_id":   att.get("TransitGatewayId"),
            "resource_id_attached": att.get("ResourceId"),
            "resource_type_attached": att.get("ResourceType"),  # vpc | vpn | directconnect
            "state":                att.get("State"),
            "association_state":    att.get("Association", {}).get("State"),
            "route_table_id":       att.get("Association", {}).get("TransitGatewayRouteTableId"),
            "tags":                 att.get("Tags", []),
        })
 
    logger.info(f"  Transit Gateway ({region}): {len(results)} resources")
    return results