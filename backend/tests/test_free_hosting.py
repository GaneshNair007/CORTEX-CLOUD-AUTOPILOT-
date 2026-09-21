"""Free hosting regression checks without downloading a model."""
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient


def test_cross_origin_console_headers():
    from backend.api_server import app
    from backend.config.settings import settings
    client = TestClient(app)
    origin = settings.cors_origins[0]
    response = client.options('/api/v1/evidence/retrieve', headers={
        'Origin': origin, 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,content-type,x-correlation-id'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == origin
    assert client.options('/api/v1/evidence/retrieve', headers={
        'Origin': 'https://untrusted.invalid',
        'Access-Control-Request-Method': 'POST'}).status_code == 400


def test_onnx_runtime_selects_cpu_without_torch(monkeypatch, tmp_path):
    from backend.rag.index import ChromaIndex
    monkeypatch.setenv('CORTEX_EMBEDDING_RUNTIME', 'onnx')
    adapter = ChromaIndex(tmp_path)
    embedding = adapter.embedding()
    assert embedding.name() == 'onnx_mini_lm_l6_v2'
    assert adapter.embedding() is embedding


def test_invalid_embedding_runtime_rejected(monkeypatch, tmp_path):
    from backend.rag.index import ChromaIndex
    monkeypatch.setenv('CORTEX_EMBEDDING_RUNTIME', 'typo')
    with pytest.raises(ValueError, match='CORTEX_EMBEDDING_RUNTIME'):
        ChromaIndex(tmp_path).embedding()


def test_low_memory_embedding_forces_single_document_batch(monkeypatch):
    from backend.rag.onnx_embedding import LowMemoryMiniLM, ONNXMiniLM_L6_V2
    forward = Mock(return_value='vectors')
    monkeypatch.setattr(ONNXMiniLM_L6_V2, '_forward', forward)
    embedding = LowMemoryMiniLM()
    assert embedding._forward(['a', 'b'], batch_size=100) == 'vectors'
    forward.assert_called_once_with(['a', 'b'], batch_size=1)
