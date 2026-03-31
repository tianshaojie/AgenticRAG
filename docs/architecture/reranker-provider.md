# Reranker Provider Integration

## Scope

This layer provides a replaceable reranker adapter for retrieval-stage reranking without leaking provider HTTP schema into retrieval/business flow.

## Components

1. `app/reranker/interfaces.py`
- provider-neutral request/response models
- `RerankerProvider` protocol

2. `app/reranker/http_provider.py`
- HTTP adapter with:
  - full endpoint mode or base URL + path mode
  - timeout + retry
  - structured logging
  - domain error mapping

3. `app/reranker/mock_provider.py`
- deterministic local provider for tests/offline

4. `app/reranker/factory.py`
- selects mock/real provider from settings
- validates API key/endpoint when real provider is enabled

5. `app/retrieval/reranker.py`
- provider-backed rerank hook (`ProviderBackedReranker`)
- fallback to original retrieval order when provider fails

## Configuration

- `reranker_provider`
- `reranker_api_key`
- `reranker_base_url`
- `reranker_endpoint`
- `reranker_model`
- `reranker_timeout_seconds`
- `reranker_max_retries`
- `reranker_top_n`
- `reranker_app_code`
- `reranker_app_name`
- `reranker_instruct`
- `enable_real_reranker_provider`
- `enable_reranking`

## Request Mapping

Input candidates are mapped to provider `documents` string array in original retrieval order.

Request body shape:

```json
{
  "app_code": "chatbi_reranker",
  "app_name": "妙查-重排",
  "query": "...",
  "model": "qwen3-reranker-8b",
  "documents": ["...", "..."],
  "instruct": "Please rerank the documents based on the query.",
  "top_n": 3
}
```

## Response Mapping

Provider response rows are mapped back to original candidate IDs via index/id/text matching, producing:

- `candidate_id`
- `original_index`
- `rank`
- optional `score`

Reranker is reorder-only; it does not create or mutate evidence identity.

## Error Mapping

1. `401/403` -> `reranker_authentication_failure`
2. timeout -> `reranker_timeout`
3. malformed payload -> `reranker_invalid_response`
4. transport failures -> `reranker_provider_unavailable`
5. `5xx` -> `reranker_upstream_server_error`
6. empty result -> `reranker_empty_result`
7. partial result -> `reranker_partial_result`

## Fallback Behavior

If provider call fails or response is invalid/partial, rerank stage falls back to original pgvector retrieval order.
