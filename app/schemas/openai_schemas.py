from datetime import datetime
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(..., description="Number of tokens used in the prompt")
    completion_tokens: int = Field(..., description="Number of tokens used in the completion")
    total_tokens: int = Field(..., description="Total number of tokens used")
    estimated_cost_usd: float = Field(..., description="Estimated cost in USD")

class OpenAISummaryResponse(BaseModel):
    summary: str = Field(..., description="The generated summary text")
    token_usage: TokenUsage = Field(..., description="Token usage information")
    model: str = Field(..., description="The OpenAI model used for generation")
    created: datetime = Field(..., description="Timestamp when the summary was created")