#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import aws_cdk as cdk
from infrastructure.infrastructure_stack import InfrastructureStack

# Load .env variables
load_dotenv()

# Validate required env vars
assert os.getenv("AWS_ACCOUNT_ID"), "Missing AWS_ACCOUNT_ID in .env"
assert os.getenv("AWS_REGION"), "Missing AWS_REGION in .env"

app = cdk.App()

InfrastructureStack(
    app,
    "InfrastructureStack",
    env=cdk.Environment(
        account=os.getenv("AWS_ACCOUNT_ID"),
        region=os.getenv("AWS_REGION")
    )
)

app.synth()