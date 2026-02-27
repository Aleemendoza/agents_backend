"""Smoke tests for EAR MVP."""

from fastapi.testclient import TestClient

from app.main import app


def test_version_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get('/v1/version')
        assert response.status_code == 200
        payload = response.json()
        assert payload['service']
        assert payload['version']


def test_list_agents_requires_api_key() -> None:
    with TestClient(app) as client:
        response = client.get('/v1/agents')
        assert response.status_code == 401


def test_run_sample_agent() -> None:
    with TestClient(app) as client:
        response = client.post(
            '/v1/run/sample-agent',
            headers={'X-API-Key': 'supersecrettoken'},
            json={'input': {'message': 'Hola'}, 'context': {}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload['success'] is True
        assert payload['output']['response'] == 'Echo: Hola'
