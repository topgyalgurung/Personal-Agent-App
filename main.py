# CLI for the personal agent: local Ollama, read-only.

import logging

from agent_core import Session

logging.basicConfig(
    level=logging.WARNING
    # level=logging.DEBUG # during development
)


def format_turn(turn):
    if turn.error:
        return f"Error: {turn.error}"

    return turn.text


def main():
    print("=" * 40)
    print("Personal Action AI Agent")
    print("Local Ollama, read-only")
    print("=" * 40)

    print("\nType 'exit' to quit.\n")

    session = Session()

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        print(f"\n{format_turn(session.send(user_input))}\n")


if __name__ == "__main__":
    main()
