
# CLI app to begin with 

import logging 

from agent import run_agent
from router import run_with_fallback

logging.basicConfig(
    level=logging.WARNING
    # level=logging.DEBUG # during development
)

def main():
    print("=" * 40)
    print("Personal Action AI Agent")
    print("Powered by Claude, Ollama. GPT later")
    print("=" * 40)

    print("\nType 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        try:
            # answer = run_agent(user_input)
            result = run_with_fallback(user_input)

            provider = result["provider"]
            answer = result["answer"]

            print(f"\n[{provider.upper()}]")
            print(answer)
            print()

        except Exception as error:
            print(f"\nError: {error}\n")


if __name__ == "__main__":
    main()
