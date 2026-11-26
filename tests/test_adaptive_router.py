from model_router import (
    GEMINI_MODELS,
    OLLAMA_DEFAULT_MODEL,
    OPENROUTER_FREE_MODEL,
    ZAI_DEFAULT_MODEL,
    ModelRouter,
)


class FakeGemini:
    def with_options(self, **kwargs):
        return self


def make_router():
    return ModelRouter(
        FakeGemini(),
        openrouter_client=object(),
        zai_client=object(),
        ollama_client=object(),
    )


def test_default_route_is_gemini_lite_then_flash_then_free_router():
    router = make_router()
    assert [target.model for target in router.targets()] == [
        GEMINI_MODELS[0],
        GEMINI_MODELS[1],
        OPENROUTER_FREE_MODEL,
    ]


def test_adaptive_order_prefers_consistently_faster_free_provider():
    router = make_router()
    targets = {target.model: target for target in router.targets()}
    for _ in range(2):
        router._record_provider_success(targets[OPENROUTER_FREE_MODEL], 0.45)
        router._record_provider_success(targets[GEMINI_MODELS[0]], 2.1)
        router._record_provider_success(targets[GEMINI_MODELS[1]], 1.8)

    assert [target.model for target in router.targets()][0] == OPENROUTER_FREE_MODEL


def test_manual_model_selection_remains_first():
    router = make_router()
    targets = {target.model: target for target in router.targets()}
    for _ in range(3):
        router._record_provider_success(targets[OPENROUTER_FREE_MODEL], 0.3)
        router._record_provider_success(targets[GEMINI_MODELS[0]], 2.0)

    assert router.targets(GEMINI_MODELS[0])[0].model == GEMINI_MODELS[0]


def test_zai_and_ollama_are_not_automatic_fallbacks():
    router = make_router()
    automatic = [target.model for target in router.targets()]
    assert ZAI_DEFAULT_MODEL not in automatic
    assert OLLAMA_DEFAULT_MODEL not in automatic
    assert ZAI_DEFAULT_MODEL in [target.model for target in router.targets(ZAI_DEFAULT_MODEL)]
    assert OLLAMA_DEFAULT_MODEL in [target.model for target in router.targets(OLLAMA_DEFAULT_MODEL)]


def test_failure_penalty_pushes_provider_down():
    router = make_router()
    targets = {target.model: target for target in router.targets()}
    for _ in range(2):
        router._record_provider_success(targets[OPENROUTER_FREE_MODEL], 0.5)
        router._record_provider_success(targets[GEMINI_MODELS[0]], 1.0)
    router.provider_failures[OPENROUTER_FREE_MODEL] = 3

    assert [target.model for target in router.targets()][0] == GEMINI_MODELS[0]
