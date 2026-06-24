"""Azure OpenAI chat model factory for the agent layer.

This is the ONLY place that needs Azure credentials. Embeddings stay local
(fastembed); only the Curator/Guardian reasoning uses Azure OpenAI chat.
"""

from __future__ import annotations

import os
from functools import lru_cache


class AzureNotConfiguredError(RuntimeError):
    pass


def azure_is_configured() -> bool:
    return all(
        os.getenv(k)
        for k in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_CHAT_DEPLOYMENT")
    )


@lru_cache(maxsize=1)
def get_chat_llm(temperature: float = 0.1):
    """Return a cached AzureChatOpenAI instance.

    Raises AzureNotConfiguredError if the Azure env vars are missing, so the API
    can return a clean 503 instead of crashing.
    """
    if not azure_is_configured():
        raise AzureNotConfiguredError(
            "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT, "
            "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_CHAT_DEPLOYMENT in .env."
        )

    from langchain_openai import AzureChatOpenAI

    return AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
        temperature=temperature,
    )
