from schemas import TOOLS
from tool_dispatch import REGISTRY


def test_every_tool_is_a_separate_schema_entry():
    names = [tool["name"] for tool in TOOLS]

    assert names == [
        "list_events",
        "list_notes",
        "search_notes",
        "read_note",
    ]


def test_every_schema_has_a_dispatcher_entry():
    missing = {tool["name"] for tool in TOOLS} - set(REGISTRY)

    assert missing == set()


def test_every_dispatcher_entry_has_a_schema():
    undocumented = set(REGISTRY) - {tool["name"] for tool in TOOLS}

    assert undocumented == set()


def test_every_schema_has_description_and_object_input():
    for tool in TOOLS:
        assert tool["description"].strip(), tool["name"]
        assert tool["input_schema"]["type"] == "object", tool["name"]
