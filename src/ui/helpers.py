"""Utility helpers — formatting, badges, and feedback posting."""

import requests
import html as html_mod
from datetime import datetime


def fmt_time(iso_str: str) -> str:
    """Parse ISO date and return a human-readable string."""
    try:
        return datetime.fromisoformat(iso_str).strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return iso_str


def confidence_badge(conf: str) -> str:
    """Return an HTML badge for a confidence level."""
    colour = {"High": "green", "Medium": "blue", "Low": "yellow"}.get(conf, "gray")
    icon = {"High": "✅", "Medium": "🔵", "Low": "⚠️"}.get(conf, "")
    return f'<span class="badge badge-{colour}">{icon} Confidence: {conf}</span>'


def post_feedback(question: str, answer: str, rating: int, api_url: str = "http://localhost:8000") -> None:
    """Send user feedback to the API."""
    try:
        requests.post(
            f"{api_url}/feedback",
            json={"question": question, "answer": answer, "rating": rating},
            timeout=5,
        )
    except Exception:
        pass
