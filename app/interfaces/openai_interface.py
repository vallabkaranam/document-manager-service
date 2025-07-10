import os
from fastapi import HTTPException
from openai import AsyncOpenAI
from app.utils.prompt_utils import load_prompt_template

# Load API key and model from env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-3.5-turbo-0125")

# Initialize the async client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

class OpenAIInterface:
    def __init__(self):
        self.model = GPT_MODEL
        self.summary_prompt_template_path = "app/prompt_templates/summarize_bullets.txt"

    async def summarize_text(self, text: str, bullet_points: int = 5, max_tokens: int = 500) -> str:
        if not text or not text.strip():
            raise HTTPException(
                status_code=500,
                detail="No text found to summarize."
            )

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

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI API error: {str(e)}"
            )