import os
from fastapi import HTTPException
from openai import AsyncOpenAI

# Load API key and model from env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-3.5-turbo-0125")

# Initialize the async client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

class OpenAIInterface:
    def __init__(self):
        self.model = GPT_MODEL

    async def summarize_text(self, text: str, bullet_points: int = 5, max_tokens: int = 500) -> str:
        if not text or not text.strip():
            raise HTTPException(
                status_code=500,
                detail="No text found to summarize."
            )

        prompt = (
            f"Summarize the following document into {bullet_points} clear, concise bullet points:\n\n{text}"
        )

        try:
            response = await openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes documents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI API error: {str(e)}"
            )