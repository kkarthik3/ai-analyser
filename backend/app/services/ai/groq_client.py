"""
Groq AI API Client wrapper.

Handles asynchronous LLM inferences with retry capability and error handling.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GroqClient:
    """Async wrapper client for Groq API inferences."""

    def __init__(self) -> None:
        self._api_key = settings.groq_api_key
        self._model = settings.groq_model
        self._client: Optional[AsyncGroq] = None

    def _get_client(self) -> AsyncGroq:
        """Get or initialize the AsyncGroq client."""
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY is not configured in settings.")
        if self._client is None:
            self._client = AsyncGroq(api_key=self._api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Generate chat completions from Groq with retry handling.
        """
        client = self._get_client()

        logger.info(f"Sending completion request to Groq using model {self._model}")
        response = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens
        }
