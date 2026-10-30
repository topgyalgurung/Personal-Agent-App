# stretch goal 
# use litellm as intelligent LLM Router, for build a reusable Cost-Aware Multi-LLM Agent Gateway.

# import os
# from litellm import completion

import os
import logging
import anthropic

from agent import run_agent
from ollama_agent import run_ollama_agent


logger = logging.getLogger(__name__)

# MODELS = {
#     "cheap": "openai/gpt-6-luna",
#     "advanced": "anthropic/claude-sonnet-4-6",
# }

FALLBACK_ERRORS = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.AuthenticationError,
)

# def classify_task(task: str) -> str:
#     """Simple routing baseline."""
#     advanced_keywords = [
#         "analyze",
#         "complex",
#         "compare",
#         "reason",
#         "plan",
#     ]

#     if any(word in task.lower()
#            for word in advanced_keywords):
#         return "advanced"

#     return "cheap"


# def run_agent(task: str):
#     tier = classify_task(task)
#     model = MODELS[tier]

#     response = completion(
#         model=model,
#         messages=[
#             {
#                 "role": "system",
#                 "content": (
#                     "You are a helpful personal "
#                     "productivity assistant."
#                 ),
#             },
#             {
#                 "role": "user",
#                 "content": task,
#             },
#         ],
#     )

#     return {
#         "model": model,
#         "response": response.choices[0].message.content,
#         "usage": response.usage,
#     }

def run_with_fallback(user_message: str):
    provider = os.getenv("LLM_PROVIDER", "claude").lower()

    if provider == "ollama":
        return {
            "provider": "ollama",
            "answer": run_ollama_agent(user_message),
        }

    try:
        return {
            "provider": "claude",
            "answer": run_agent(user_message),
        }

    except FALLBACK_ERRORS as error:
        logger.debug(
            "Claude failed (%s). Switching to Ollama.",
            type(error).__name__,
        )

        return {
            "provider": "ollama",
            "answer": run_ollama_agent(user_message),
        }
    
if __name__ == "__main__":
    result = run_agent(
        "Summarize my tasks for today"
    )

    print("Model:", result["model"])
    print(result["response"])

