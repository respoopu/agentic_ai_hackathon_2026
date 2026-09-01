"""Runtime constants kept outside model and graph judgement."""

from __future__ import annotations

import os

MAX_REPLANS = 3
MAX_DISCOVERY_ROUNDS = 2
MAX_GUARDIAN_REJECTIONS = 2
MAX_LISTINGS_PER_SCAN = 50
MAX_FETCHES_PER_DOMAIN = 5

DEFAULT_AWS_REGION = "ap-southeast-1"
DEFAULT_MODEL_ID = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
REASONING_MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

DISCOVERY_ALLOWED_DOMAINS = frozenset(
    {
        "activesg.gov.sg",
        "nlb.gov.sg",
        "nlb.libcal.com",
        "onepa.gov.sg",
        "pa.gov.sg",
        "scape.sg",
        "sportssg.gov.sg",
    }
)


def aws_region() -> str:
    return os.getenv("AWS_REGION", DEFAULT_AWS_REGION)
