from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'ok'
    assert body['service'] == 'agentic-rag-backend'


def test_ready_endpoint() -> None:
    response = client.get('/ready')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] in {'ok', 'degraded'}
    assert 'database' in body['checks']


def test_required_routes_present_in_openapi() -> None:
    response = client.get('/openapi.json')
    assert response.status_code == 200
    paths = response.json()['paths']

    expected = {
        '/documents',
        '/documents/{id}/index',
        '/chat/query',
        '/chat/{id}/trace',
        '/health',
        '/ready',
        '/evals/run',
        '/evals/{id}',
    }
    assert expected.issubset(set(paths.keys()))


def test_chat_query_defaults_to_abstain() -> None:
    response = client.post('/chat/query', json={'query': 'test query'})
    assert response.status_code == 200
    body = response.json()
    assert body['abstained'] is True
    assert isinstance(body['citations'], list)
