#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import aws_cdk as cdk
from infrastructure.infrastructure_stack import InfrastructureStack

# Load environment variables from .env
load_dotenv()

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