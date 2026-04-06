import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)

def scan_acm(session, region):
    logger.info(f"Scanning ACM in {region}...")
    client = session.client("acm", region_name=region)
    results = []
 
    cert_arns = paginate(client, "list_certificates", "CertificateSummaryList")
    for cert_summary in cert_arns:
        cert_arn = cert_summary.get("CertificateArn")
 
        # Full certificate details
        detail_resp = safe_call(client.describe_certificate, CertificateArn=cert_arn)
        if not detail_resp:
            continue
        cert = detail_resp.get("Certificate", {})
 
        # Tags
        tags_resp = safe_call(client.list_tags_for_certificate, CertificateArn=cert_arn)
 
        results.append({
            "resource_type":          "acm_certificate",
            "resource_id":            cert_arn,
            "resource_name":          cert.get("DomainName"),
            "region":                 region,
            "domain_name":            cert.get("DomainName"),
            "subject_alternative_names": cert.get("SubjectAlternativeNames", []),
            "status":                 cert.get("Status"),       # ISSUED | EXPIRED | PENDING_VALIDATION
            "type":                   cert.get("Type"),         # AMAZON_ISSUED | IMPORTED
            "issuer":                 cert.get("Issuer"),
            "key_algorithm":          cert.get("KeyAlgorithm"),
            "signature_algorithm":    cert.get("SignatureAlgorithm"),
            "not_before":             cert.get("NotBefore").isoformat() if cert.get("NotBefore") else None,
            "not_after":              cert.get("NotAfter").isoformat() if cert.get("NotAfter") else None,
            "renewal_eligibility":    cert.get("RenewalEligibility"),
            "in_use_by":              cert.get("InUseBy", []),   # which services are using it
            "validation_method":      cert.get("DomainValidationOptions", [{}])[0].get("ValidationMethod")
                                       if cert.get("DomainValidationOptions") else None,
            "tags":                   tags_resp.get("Tags", []) if tags_resp else [],
        })
 
    logger.info(f"  ACM ({region}): {len(results)} certificates")
    return results