# LLM Provider Integration

## Scope

This layer provides a replaceable LLM adapter for answer generation without leaking provider specifics into business flow.

## Components

1. `app/llm/interfaces.py`
- `LLMProvider` protocol
- request/response/message schemas

2. `app/llm/openai_compatible.py`
- HTTP adapter for OpenAI Chat Completions compatible endpoints
- supports:
  - full endpoint URL mode
  - base URL + path mode
  - timeout + retry
  - structured logging
  - error mapping

3. `app/llm/mock_provider.py`
- deterministic offline provider for tests/evals/local development

4. `app/llm/factory.py`
- switches mock/real provider based on settings
- validates required API key when real provider enabled

5. `app/services/answer_factory.py`
- injects selected provider into `ThresholdAnswerGenerator`

## Configuration

Settings fields:

- `llm_provider`
- `llm_api_key`
- `llm_base_url`
- `llm_endpoint`
- `llm_model`
- `llm_timeout_seconds`
- `llm_max_retries`
- `llm_temperature`
- `llm_max_tokens`
- `enable_real_llm_provider`

## Error Mapping

1. `401/403` -> `llm_authentication_failure`
2. timeout -> `llm_timeout`
3. malformed payload -> `llm_invalid_response`
4. `429` -> `llm_rate_limited`
5. `5xx` -> `llm_upstream_server_error`
6. transport failures -> `llm_provider_unavailable`

All mappings convert to domain-level `AppError` subclasses.

## Abstain-First Guarantee

`ThresholdAnswerGenerator` evaluates evidence count/score first.  
If evidence is insufficient, it returns abstain and does not call LLM provider.
