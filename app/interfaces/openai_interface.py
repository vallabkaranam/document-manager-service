"""
OpenAI Interface Module

Provides an abstraction over OpenAI API operations including text summarization and
grounded question-answering using GPT models. This interface ensures consistent error
handling and encapsulates all OpenAI-related logic behind a single class.

Key Capabilities:
- Summarize text into bullet points using GPT models
- Answer queries grounded in contextual input using RAG-style prompting
- Track token usage and cost
- Ensure validation and exception safety across operations

Assumptions:
- Environment variable OPENAI_API_KEY is configured
- Model and prompt template paths are configurable
- All inputs and outputs are validated Pydantic models
"""

from datetime import UTC, datetime
import os
from openai import AsyncOpenAI
from app.schemas.openai_schemas import OpenAISummaryResponse, OpenAIRAGAnswerResponse, TokenUsage
from app.utils.prompt_utils import load_prompt_template
from app.schemas.errors import OpenAIServiceError

# Load API key and model from env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-3.5-turbo-0125")

# Initialize the async client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

class OpenAIInterface:
    """
    Provides an abstraction over OpenAI operations, ensuring consistent error handling
    and encapsulating all OpenAI-related logic behind a single class.
    """
    def __init__(self) -> None:
        """
        Initializes the OpenAI interface with model and prompt template paths.
        """
        self.model = GPT_MODEL
        self.summary_prompt_template_path = "app/prompt_templates/summarize_bullets.txt"
        self.rag_prompt_template_path = "app/prompt_templates/answer_from_context.txt"

    async def summarize_text(self, text: str, bullet_points: int = 5, max_tokens: int = 500) -> OpenAISummaryResponse:
        """
        Summarizes the input text into bullet points using OpenAI GPT models.

        Args:
            text (str): The text to summarize.
            bullet_points (int): Number of bullet points to generate (default: 5).
            max_tokens (int): Maximum tokens for the summary (default: 500).

        Returns:
            OpenAISummaryResponse: The summary, token usage, model, and creation time.

        Raises:
            OpenAIServiceError: If the OpenAI API call fails or input is invalid.
        """
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

    async def generate_answer(self, query: str, context: str, max_tokens: int = 500) -> OpenAIRAGAnswerResponse:
        """
        Generates a grounded answer to a user query based on retrieved context using OpenAI GPT models.

        Args:
            query (str): The user question to be answered.
            context (str): The supporting context to ground the response.
            max_tokens (int): Maximum tokens for the generated answer (default: 500).

        Returns:
            OpenAIRAGAnswerResponse: The generated answer, token usage, model, and creation time.

        Raises:
            OpenAIServiceError: If the OpenAI API call fails or input is invalid.
        """
        if not query or not context or not query.strip() or not context.strip():
            raise OpenAIServiceError("Query and context must be provided for RAG-based answer generation.")

        try:
            prompt_template = load_prompt_template(self.rag_prompt_template_path)
            prompt = prompt_template.format(query=query, context=context)

            response = await openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that only answers based on provided context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens
            )

            answer = response.choices[0].message.content.strip()
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

            return OpenAIRAGAnswerResponse(
                answer=answer,
                token_usage=token_usage,
                model=model,
                created=created
            )

        except Exception as e:
            raise OpenAIServiceError(f"OpenAI API error during RAG answer generation: {str(e)}") from e