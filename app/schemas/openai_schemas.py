from datetime import datetime
from pydantic import BaseModel


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float

class OpenAISummaryResponse(BaseModel):
    summary: str
    token_usage: TokenUsage
    model: str
    created: datetime