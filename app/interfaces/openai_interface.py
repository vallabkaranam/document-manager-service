from datetime import UTC, datetime
import os
from fastapi import HTTPException
from openai import AsyncOpenAI
from app.schemas.openai_schemas import OpenAISummaryResponse, TokenUsage
from app.utils.prompt_utils import load_prompt_template

# Load API key and model from env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-3.5-turbo-0125")

# Initialize the async client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

class OpenAIServiceError(Exception):
    """Raised when OpenAI API call fails"""
    pass

class OpenAIInterface:
    def __init__(self):
        self.model = GPT_MODEL
        self.summary_prompt_template_path = "app/prompt_templates/summarize_bullets.txt"

    async def summarize_text(self, text: str, bullet_points: int = 5, max_tokens: int = 500) -> OpenAISummaryResponse:
        if not text or not text.strip():
            raise OpenAIServiceError("No text found to summarize.")

        try:
            # Load and render the prompt template
            prompt_template = load_prompt_template(self.summary_prompt_template_path)
            prompt = prompt_template.format(text=text, bullet_points=bullet_points)

            # Call OpenAI async chat completion
            response = await openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes documents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens
            )

            summary = response.choices[0].message.content.strip()
            token_usage_dict = {
                  "prompt_tokens": response.usage.prompt_tokens,
                  "completion_tokens": response.usage.completion_tokens,
                  "total_tokens": response.usage.total_tokens,
                  "estimated_cost_usd": round(
                    (response.usage.prompt_tokens * 0.0005 / 1000) +
                    (response.usage.completion_tokens * 0.0015 / 1000), 6
                    )
            }
            token_usage = TokenUsage.model_validate(token_usage_dict)
            model = response.model
            created = datetime.fromtimestamp(response.created, tz=UTC)

            return OpenAISummaryResponse(
                summary=summary,
                token_usage=token_usage,
                model=model,
                created=created
            )

        except Exception as e:
            raise OpenAIServiceError(f"OpenAI API error: {str(e)}") from e