from agent_core import Turn
from main import format_turn


def test_format_turn_shows_the_answer():
    turn = Turn(id="1", provider="ollama", text="You have 2 notes.")

    assert format_turn(turn) == "You have 2 notes."


def test_format_turn_shows_the_error_when_there_is_no_answer():
    turn = Turn(
        id="1",
        provider="ollama",
        text="",
        error="Ollama isn't running. Start it with: ollama serve",
    )

    assert format_turn(turn) == (
        "Error: Ollama isn't running. Start it with: ollama serve"
    )
