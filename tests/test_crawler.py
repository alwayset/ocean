"""Tests for the MCP crawler."""

from src.crawler.mcp import extract_tools_from_server_json


def test_extract_tools_basic():
    data = {
        "name": "test-server",
        "tools": [
            {
                "name": "search",
                "description": "Search for items",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            },
            {
                "name": "create",
                "description": "Create an item",
            },
        ],
    }
    tools = extract_tools_from_server_json(data)
    assert len(tools) == 2
    assert tools[0]["name"] == "search"
    assert tools[0]["input_schema"]["type"] == "object"
    assert tools[1]["name"] == "create"


def test_extract_tools_nested():
    data = {
        "capabilities": {
            "tools": [
                {"name": "read", "description": "Read a file"},
            ]
        }
    }
    tools = extract_tools_from_server_json(data)
    assert len(tools) == 1
    assert tools[0]["name"] == "read"


def test_extract_tools_empty():
    assert extract_tools_from_server_json({}) == []
    assert extract_tools_from_server_json({"tools": []}) == []


def test_extract_tools_malformed():
    data = {"tools": [{"not_a_tool": True}, {"name": "valid", "description": "ok"}]}
    tools = extract_tools_from_server_json(data)
    assert len(tools) == 1
    assert tools[0]["name"] == "valid"
