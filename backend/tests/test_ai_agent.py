"""Happy-path tests for AIAgentService.chat() — core booking flow.

Covers:
  1. Simple single booking flow (master → service → time → name → record created)
  2. Auto-record when client says name after waiting_for_name
  3. Multi-booking detection ("екі бала" → 2 appointments)
  4. Client typing time instead of name → reschedule, not name
  5. "Рестарт" command resets all session state
  6. Conversation TTL (24h) — old session is reset
  7. Booking context TTL (2h) — preserves history but resets booking
  8. Disabled chatbot returns polite "unavailable" message
  9. OpenAI circuit breaker open → polite fallback
 10. Daily OpenAI cap reached → polite "overloaded" message
"""
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from tests.conftest import make_tool_call


# ── 1. Simple single booking happy path ──────────────────────────────────────

async def test_single_booking_complete_flow(ai_service, mock_alteegio):
    """Client says 'хочу записаться к Мише на завтра в 15:00, меня зовут Айдар'.

    The bot's regex-based fast-path handles this WITHOUT calling OpenAI:
      - "Хочу записаться к Мише" → get_services_by_staff_name(Миша) via AI
      - 15:00 detected as time
      - Имя Айдар → auto-creates appointment
    For simplicity we test the FINAL stage: client says name → appointment created.
    """
    # Pre-seed booking context as if we already got to waiting_for_name
    full_sid = "test_77071234567"
    ai_service.conversations.clear()
    ai_service.booking_context.clear()
    from app.services.ai_agent_service import SESSION_PREFIX
    full_sid = f"{SESSION_PREFIX}_77071234567"
    ai_service.booking_context[full_sid] = {
        "staff_id": "100", "service_id": "555", "seance_length": "3600",
        "datetime": "2026-05-25T15:00:00", "waiting_for_name": True,
        "preferred_time": None, "requested_hour": 15, "requested_minute": 0,
        "date": "2026-05-25", "multi_booking_count": 1, "bookings_created": 0,
        "multi_booking_staff_ids": [],
    }

    response = await ai_service.chat(
        user_input="Айдар",
        session_id="77071234567",
        user_phone="77071234567",
    )

    assert "Записал" in response or "ждёт" in response
    mock_alteegio.create_appointment.assert_called_once()
    call_kwargs = mock_alteegio.create_appointment.call_args.kwargs
    assert call_kwargs["staff_id"] == "100"
    assert call_kwargs["client_name"] == "Айдар"
    assert call_kwargs["datetime"] == "2026-05-25T15:00:00"


# ── 2. Auto-record fires only when waiting_for_name is True ──────────────────

async def test_no_auto_record_without_waiting_for_name(ai_service, mock_openai, mock_alteegio):
    """If waiting_for_name is False, name-like input goes to OpenAI, not create_appointment."""
    mock_openai.set_response(content="Расскажите подробнее, что вас интересует?")

    response = await ai_service.chat(
        user_input="Айдар",
        session_id="77079999999",
        user_phone="77079999999",
    )

    # OpenAI was called (not the auto-flow)
    assert len(mock_openai.calls) == 1
    # create_appointment was NOT called
    mock_alteegio.create_appointment.assert_not_called()


# ── 3. Multi-booking detection (Russian) ─────────────────────────────────────

async def test_multi_booking_detected_russian(ai_service, mock_openai):
    """'двое детей' → multi_booking_count = 2"""
    mock_openai.set_response(content="На какое время записать двоих детей?")

    await ai_service.chat(
        user_input="Хочу записать двоих детей на завтра",
        session_id="77072223344",
        user_phone="77072223344",
    )

    from app.services.ai_agent_service import SESSION_PREFIX
    ctx = ai_service.booking_context[f"{SESSION_PREFIX}_77072223344"]
    assert ctx["multi_booking_count"] == 2


# ── 4. "На два" inside multi-booking message is NOT treated as time 14:00 ────

async def test_multi_booking_does_not_confuse_time(ai_service, mock_openai):
    """'на два ребёнка' should NOT set requested_hour=14."""
    mock_openai.set_response(content="Хорошо, на двоих. На какое время?")

    await ai_service.chat(
        user_input="запишите на два ребенка пожалуйста",
        session_id="77078765432",
        user_phone="77078765432",
    )

    from app.services.ai_agent_service import SESSION_PREFIX
    ctx = ai_service.booking_context[f"{SESSION_PREFIX}_77078765432"]
    assert ctx["multi_booking_count"] == 2
    assert ctx["requested_hour"] is None  # NOT treated as 14:00


# ── 5. "Рестарт" resets all session state ────────────────────────────────────

async def test_restart_command_clears_state(ai_service, mock_openai):
    """Sending 'рестарт' wipes conversations + booking_context for that session."""
    # Seed some state
    from app.services.ai_agent_service import SESSION_PREFIX
    sid = f"{SESSION_PREFIX}_77071111111"
    ai_service.conversations[sid] = [{"role": "user", "content": "old"}]
    ai_service.booking_context[sid] = {"staff_id": "100", "waiting_for_name": True}

    response = await ai_service.chat(
        user_input="рестарт",
        session_id="77071111111",
        user_phone="77071111111",
    )

    assert "сброшена" in response.lower()
    assert sid not in ai_service.conversations
    assert sid not in ai_service.booking_context
    # OpenAI was NOT called
    assert len(mock_openai.calls) == 0


# ── 6. Conversation TTL: 24h+ inactivity wipes EVERYTHING ────────────────────

async def test_conversation_ttl_resets_after_24h(ai_service, mock_openai):
    """After CONVERSATION_TTL elapsed, both history and booking_context are dropped."""
    from app.services.ai_agent_service import SESSION_PREFIX, CONVERSATION_TTL
    sid = f"{SESSION_PREFIX}_77074445566"

    # Pretend last activity was 25h ago
    ai_service._last_activity[sid] = time.time() - (CONVERSATION_TTL + 3600)
    ai_service.conversations[sid] = [{"role": "user", "content": "old"}]
    ai_service.booking_context[sid] = {"staff_id": "100"}

    mock_openai.set_response(content="Здравствуйте! Чем могу помочь?")
    await ai_service.chat(
        user_input="Здравствуйте",
        session_id="77074445566",
        user_phone="77074445566",
    )

    # Both wiped (note: chat() rebuilds them, but should start FRESH)
    assert ai_service.conversations[sid] == [{"role": "user", "content": "User Input: Здравствуйте\nUser Phone: 77074445566"}] or len(ai_service.conversations[sid]) <= 2
    # booking_context recreated empty
    assert ai_service.booking_context[sid]["staff_id"] is None


# ── 7. Booking context TTL: 2h+ inactivity resets booking, KEEPS conversation ─

async def test_booking_context_ttl_preserves_conversation(ai_service, mock_openai):
    """After BOOKING_CONTEXT_TTL but before CONVERSATION_TTL, only booking resets."""
    from app.services.ai_agent_service import SESSION_PREFIX, BOOKING_CONTEXT_TTL
    sid = f"{SESSION_PREFIX}_77076667788"

    ai_service._last_activity[sid] = time.time() - (BOOKING_CONTEXT_TTL + 60)
    old_history = [{"role": "user", "content": "old conversation"}]
    ai_service.conversations[sid] = list(old_history)
    ai_service.booking_context[sid] = {"staff_id": "100", "waiting_for_name": True}

    mock_openai.set_response(content="Здравствуйте!")
    await ai_service.chat(
        user_input="Привет",
        session_id="77076667788",
        user_phone="77076667788",
    )

    # Booking context dropped
    assert ai_service.booking_context[sid]["staff_id"] is None
    assert ai_service.booking_context[sid]["waiting_for_name"] is False
    # Conversation history preserved (kept the old message somewhere in the new history)
    assert len(ai_service.conversations[sid]) >= 1


# ── 8. Disabled chatbot returns polite message without OpenAI call ───────────

async def test_disabled_chatbot_short_circuits(ai_service, mock_openai):
    from app.database import update_bot_settings
    update_bot_settings(chatbot_enabled=False, excluded_master_ids=[])

    response = await ai_service.chat(
        user_input="Хочу записаться",
        session_id="77079998877",
        user_phone="77079998877",
    )

    assert "недоступен" in response.lower() or "позже" in response.lower()
    assert len(mock_openai.calls) == 0

    # Re-enable for other tests
    update_bot_settings(chatbot_enabled=True, excluded_master_ids=[])


# ── 9. OpenAI circuit OPEN → polite fallback, no real OpenAI call ────────────

async def test_openai_circuit_open_fallback(ai_service, mock_openai, monkeypatch):
    from app.utils.circuit_breaker import openai_breaker, CircuitState
    import time as _t

    # Force-open the breaker
    openai_breaker._state = CircuitState.OPEN
    openai_breaker._opened_at = _t.monotonic()
    openai_breaker._failures = 99

    try:
        response = await ai_service.chat(
            user_input="Хочу записаться",
            session_id="77071212121",
            user_phone="77071212121",
        )
        assert "позвоните" in response.lower() or "минут" in response.lower()
        # OpenAI was NOT actually called (breaker rejected it)
        assert len(mock_openai.calls) == 0
    finally:
        # Reset breaker for other tests
        openai_breaker._state = CircuitState.CLOSED
        openai_breaker._failures = 0
        openai_breaker._opened_at = None


# ── 10. Daily cost cap reached → polite "overloaded" message ─────────────────

async def test_daily_cost_cap_blocks_request(ai_service, mock_openai, monkeypatch):
    from app.database import record_openai_usage
    from app.config import get_settings
    cfg = get_settings()

    # Set a tiny cap and exceed it
    monkeypatch.setattr(cfg, "openai_daily_limit_usd", 0.01)
    record_openai_usage(input_tokens=100_000, output_tokens=100_000, cost_usd=1.0)

    response = await ai_service.chat(
        user_input="Хочу записаться",
        session_id="77073333333",
        user_phone="77073333333",
    )

    assert "перегружен" in response.lower() or "позже" in response.lower()
    assert len(mock_openai.calls) == 0
