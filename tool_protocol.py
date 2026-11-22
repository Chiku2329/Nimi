"""Build standards-compliant assistant/tool messages for OpenAI-compatible APIs."""


def build_tool_exchange(assistant_text, calls, results, round_no):
    """Return one assistant tool-call message followed by matching tool results.

    The provider requires tool results to reference the exact call IDs emitted by
    the assistant. Deterministic fallback IDs cover compatible providers that
    omit IDs in streamed deltas.
    """
    if len(calls) != len(results):
        raise ValueError("Every tool call must have exactly one result.")

    tool_calls = []
    tool_messages = []
    used_ids = set()

    for index, (call, result) in enumerate(zip(calls, results)):
        name = call.get("name")
        arguments = call.get("args") or "{}"
        call_id = call.get("id") or f"nimi_tool_{round_no}_{index}"

        if not isinstance(name, str) or not name:
            raise ValueError("Tool call is missing a function name.")
        if not isinstance(arguments, str):
            raise ValueError("Tool arguments must remain a JSON string.")
        if not isinstance(call_id, str) or not call_id or call_id in used_ids:
            call_id = f"nimi_tool_{round_no}_{index}"
        if call_id in used_ids:
            raise ValueError("Tool call IDs must be unique.")

        used_ids.add(call_id)
        tool_calls.append({
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": arguments},
        })
        tool_messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "content": str(result)[:6000],
        })

    assistant_message = {
        "role": "assistant",
        "content": assistant_text or None,
        "tool_calls": tool_calls,
    }
    return [assistant_message, *tool_messages]
