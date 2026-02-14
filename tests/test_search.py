"""Tests for the search/embedding module."""

from src.search.embeddings import build_tool_text


def test_build_tool_text_full():
    text = build_tool_text("searchFlights", "Search available flights", "booking.com")
    assert "searchFlights" in text
    assert "Search available flights" in text
    assert "booking.com" in text


def test_build_tool_text_no_provider():
    text = build_tool_text("sendEmail", "Send an email")
    assert "sendEmail" in text
    assert "Send an email" in text
    assert "Provider" not in text
