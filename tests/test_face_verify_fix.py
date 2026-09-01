import json
import pytest
from app.services.face_recognition_service import FaceRecognitionService
from app.services.face_service import FaceService
from app.models.face_embedding import FaceEmbedding
from app.models.face_verification import FaceVerificationStatus


def test_similarity_calculation_with_list():
    """TEST 2 & 3: Validasi kalkulasi similarity dengan input list[float] 128 dimensi."""
    service = FaceRecognitionService()
    # 128-D vector
    v1 = [0.1] * 128
    v2 = [0.1] * 128
    score = service.calculate_similarity(v1, v2)
    assert isinstance(score, float)
    assert abs(score - 1.0) < 1e-4


def test_similarity_calculation_non_matching():
    """TEST 5: Validasi kalkulasi similarity dengan vektor non-matching (orthogonal/berbeda)."""
    service = FaceRecognitionService()
    v1 = [1.0] + [0.0] * 127
    v2 = [0.0] * 64 + [1.0] + [0.0] * 63
    score = service.calculate_similarity(v1, v2)
    assert isinstance(score, float)
    assert score < 0.70  # Di bawah threshold


def test_embedding_normalization_polymorphism():
    """TEST 1 & 7: Validasi normalisasi embedding baik berformat list maupun string JSON."""
    # Case A: Database mengembalikan list (PostgreSQL Native JSON)
    active_emb_list = FaceEmbedding(embedding=[0.05] * 128)
    raw_embedding_a = active_emb_list.embedding
    if isinstance(raw_embedding_a, (str, bytes, bytearray)):
        vector_a = json.loads(raw_embedding_a)
    else:
        vector_a = raw_embedding_a
    assert isinstance(vector_a, list)
    assert len(vector_a) == 128

    # Case B: Database / Mock mengembalikan JSON string (Legacy/SQLite)
    active_emb_str = FaceEmbedding(embedding=json.dumps([0.05] * 128))
    raw_embedding_b = active_emb_str.embedding
    if isinstance(raw_embedding_b, (str, bytes, bytearray)):
        vector_b = json.loads(raw_embedding_b)
    else:
        vector_b = raw_embedding_b
    assert isinstance(vector_b, list)
    assert len(vector_b) == 128

    # Similarity calculation works on both
    rec_service = FaceRecognitionService()
    sim = rec_service.calculate_similarity(vector_a, vector_b)
    assert abs(sim - 1.0) < 1e-4
