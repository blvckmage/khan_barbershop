"""Pytest fixtures: isolated SQLite DB + mocked OpenAI/Alteegio/Sheets.

Each test gets a fresh temp DB, mocked external services, and a clean
AIAgentService instance. No real API calls are ever made.
"""
import os
import sys
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# ── Set required env vars BEFORE importing app modules ───────────────────────
os.environ.setdefault("ALTEEGIO_BEARER_TOKEN", "test_bearer")
os.environ.setdefault("ALTEEGIO_USER_TOKEN", "test_user")
os.environ.setdefault("ALTEEGIO_COMPANY_ID", "12345")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("OPENAI_MODEL", "gpt-4.1-mini")
os.environ.setdefault("STAFF_SPREADSHEET_ID", "test_staff_sheet")
os.environ.setdefault("SERVICES_SPREADSHEET_ID", "test_services_sheet")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "test_phone")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "test_token")
os.environ.setdefault("OPENAI_DAILY_LIMIT_USD", "0")  # no cap in tests

# Make `app.*` importable from tests/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test gets a fresh, temporary SQLite database."""
    db_path = tmp_path / "test_khan.db"
    monkeypatch.setattr("app.database.DATABASE_PATH", str(db_path))
    # Re-init schema
    from app.database import init_db
    init_db()
    yield db_path


def _get_ai_module():
    """Get the actual ai_agent_service MODULE (not the singleton with the same name).

    Because app/services/__init__.py does `from .ai_agent_service import ai_agent_service`,
    the attribute lookup `app.services.ai_agent_service` returns the SINGLETON, not the
    module. We must use sys.modules to get the module itself.
    """
    import sys
    # Trigger import if not yet loaded
    import app.services.ai_agent_service  # noqa: F401
    return sys.modules["app.services.ai_agent_service"]


def _get_broadcast_module():
    import sys
    import app.services.broadcast_service  # noqa: F401
    return sys.modules["app.services.broadcast_service"]


@pytest.fixture
def mock_alteegio(monkeypatch):
    """Mock alteegio_service — no real API calls."""
    mock = MagicMock()
    mock.get_records = AsyncMock(return_value=[])
    mock.get_staff = AsyncMock(return_value=[])
    mock.get_available_times = AsyncMock(return_value={"data": []})
    mock.get_available_dates = AsyncMock(return_value={"data": []})
    mock.get_available_masters = AsyncMock(return_value=[])
    mock.create_appointment = AsyncMock(return_value={
        "success": True,
        "data": {"id": 999, "staff": {"name": "Миша"}, "date": "2026-05-25 14:00:00"}
    })
    mock.get_clients = AsyncMock(return_value=[])
    mock.get_clients_with_future_appointments = AsyncMock(return_value=set())
    mock.get_appointments_for_period = AsyncMock(return_value=[])
    mock.get_past_appointments_for_date = AsyncMock(return_value=[])
    mock.client_has_future_appointment = AsyncMock(return_value=False)
    monkeypatch.setattr(_get_ai_module(), "alteegio_service", mock)
    monkeypatch.setattr(_get_broadcast_module(), "alteegio_service", mock)
    return mock


@pytest.fixture
def mock_sheets(monkeypatch):
    """Mock Google Sheets service."""
    mock = MagicMock()
    mock.get_all_staff = MagicMock(return_value=[
        {"staff_id": "100", "name": "Миша"},
        {"staff_id": "101", "name": "Нурдаулет"},
        {"staff_id": "102", "name": "Наргиза"},
    ])
    mock.get_services_by_staff_name = MagicMock(side_effect=lambda name: (
        [{
            "service_id": "555", "service_name": "Стрижка мужская",
            "staff_id": "100", "staff_name": "Миша",
            "seance_length": 3600, "price": 5000,
        }] if "миш" in name.lower() else
        [{
            "service_id": "556", "service_name": "Стрижка мужская",
            "staff_id": "101", "staff_name": "Нурдаулет",
            "seance_length": 3600, "price": 5000,
        }] if "нурдаулет" in name.lower() else []
    ))
    mock.get_services_by_name = MagicMock(return_value=[])
    monkeypatch.setattr(_get_ai_module(), "sheets_service", mock)
    return mock


@pytest.fixture
def mock_openai(monkeypatch):
    """Mock OpenAI client. Tests configure responses per-case via set_response()."""

    class _MockOpenAIClient:
        def __init__(self):
            self.responses = []  # FIFO queue of responses
            self.calls = []

            class _ChatNamespace:
                def __init__(s, outer):
                    s._outer = outer
                    class _Completions:
                        def create(s2, **kwargs):
                            s._outer.calls.append(kwargs)
                            if not s._outer.responses:
                                raise RuntimeError("No mocked OpenAI response queued")
                            return s._outer.responses.pop(0)
                    s.completions = _Completions()

            self.chat = _ChatNamespace(self)

        def set_response(self, content: str = None, tool_calls: list = None,
                         input_tokens: int = 100, output_tokens: int = 50):
            """Queue a single OpenAI response."""
            msg = MagicMock()
            msg.content = content
            msg.tool_calls = tool_calls
            msg.model_dump = lambda: {
                "role": "assistant",
                "content": content,
                "tool_calls": [{"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}, "type": "function"} for tc in (tool_calls or [])] if tool_calls else None,
            }

            response = MagicMock()
            response.choices = [MagicMock(message=msg)]
            response.usage = MagicMock(prompt_tokens=input_tokens, completion_tokens=output_tokens)
            self.responses.append(response)

    client = _MockOpenAIClient()

    # Patch the singleton AIAgentService.client directly.
    # NOTE: app.services.__init__ exports the singleton with the same name as
    # the module, so we import the singleton and patch its attributes.
    from app.services.ai_agent_service import ai_agent_service as _svc
    _svc.client = client
    _svc.conversations.clear()
    _svc.booking_context.clear()
    _svc._last_activity.clear()
    _svc._chat_call_counter = 0

    return client


@pytest.fixture
def ai_service(mock_openai, mock_alteegio, mock_sheets):
    """Get a clean AIAgentService instance (singleton, but state cleared)."""
    from app.services.ai_agent_service import ai_agent_service
    return ai_agent_service


def make_tool_call(name: str, arguments: dict, call_id: str = "tc_1") -> MagicMock:
    """Helper to build a mock tool_call object."""
    import json as _json
    tc = MagicMock()
    tc.id = call_id
    tc.function = MagicMock(name=name, arguments=_json.dumps(arguments))
    tc.function.name = name
    tc.function.arguments = _json.dumps(arguments)
    return tc
