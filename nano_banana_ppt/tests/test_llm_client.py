from nano_banana_ppt.utils.llm_client import chat_completion_with_fallback


class _DummyCompletions:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    def create(self, model, **kwargs):
        self.calls.append(model)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _DummyChat:
    def __init__(self, outcomes):
        self.completions = _DummyCompletions(outcomes)


class _DummyClient:
    def __init__(self, outcomes):
        self.chat = _DummyChat(outcomes)


class _Response:
    pass


def test_falls_back_on_connection_error():
    client = _DummyClient([RuntimeError("APIConnectionError: Connection error."), _Response()])

    resp = chat_completion_with_fallback(
        client,
        model_fallback=["model-a", "model-b"],
        messages=[{"role": "user", "content": "hello"}],
    )

    assert isinstance(resp, _Response)
    assert client.chat.completions.calls == ["model-a", "model-b"]


def test_falls_back_on_timeout_error():
    client = _DummyClient([RuntimeError("Request timed out."), _Response()])

    resp = chat_completion_with_fallback(
        client,
        model_fallback=["model-a", "model-b"],
        messages=[{"role": "user", "content": "hello"}],
    )

    assert isinstance(resp, _Response)
    assert client.chat.completions.calls == ["model-a", "model-b"]
