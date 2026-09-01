"""Lazy Bedrock factory; importing Hobbi never requires AWS credentials."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse

from src.constants import DEFAULT_MODEL_ID, REASONING_MODEL_ID, aws_region
from src.schema.gates import TokenUsage


def create_bedrock_model(*, reasoning: bool = False, temperature: float = 0) -> ChatBedrockConverse:
    region = aws_region().strip()
    if not region:
        raise ValueError("AWS_REGION must be a non-empty Bedrock region")
    client = boto3.client(
        "bedrock-runtime",
        config=Config(
            region_name=region,
            read_timeout=300,
            connect_timeout=120,
            retries={"max_attempts": 1},
        ),
    )
    return ChatBedrockConverse(
        model_id=REASONING_MODEL_ID if reasoning else DEFAULT_MODEL_ID,
        client=client,
        temperature=temperature,
    )


def token_usage(agent: str, message: Any) -> TokenUsage:
    usage = getattr(message, "usage_metadata", None) or {}
    return TokenUsage(
        agent=agent,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        recorded_at=datetime.now(UTC),
    )
