import boto3
import os
import logging
from functools import wraps

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def get_session():
    profile = os.getenv("AWS_PROFILE", "cloudguard-scanner")
    return boto3.Session(profile_name=profile)


# ─────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────

def safe_call(fn, *args, **kwargs):
    """
    Wraps any boto3 call. Returns the result or None if the call
    fails (e.g. service not enabled, permission denied for one resource).
    Prevents one failing service from crashing the whole scan.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Call failed: {fn.__name__ if hasattr(fn, '__name__') else fn} — {e}")
        return None


def paginate(client, method, result_key, **kwargs):
    """
    Handles AWS pagination automatically.
    Many AWS APIs return results in pages — this collects all pages
    into one flat list so the rest of the code never has to think about it.
    """
    try:
        paginator = client.get_paginator(method)
        results = []
        for page in paginator.paginate(**kwargs):
            results.extend(page.get(result_key, []))
        return results
    except Exception as e:
        logger.warning(f"Pagination failed for {method}: {e}")
        return []
    
    
def my_wrapper(func):
    @wraps(func)
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    return inner