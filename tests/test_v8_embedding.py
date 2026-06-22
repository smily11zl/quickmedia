"""Tests for V8 embedding infrastructure."""

import os
import tempfile
import pytest


class TestChromaDBIntegration:
    def test_client_creation_and_collection(self):
        """ChromaDB PersistentClient creates and reuses collections."""
        import chromadb
        d = tempfile.mkdtemp()
        try:
            client = chromadb.PersistentClient(path=d)
            coll = client.get_or_create_collection("quickmedia_test")
            coll.add(
                ids=["1", "2"],
                embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                metadatas=[{"asset_id": 1}, {"asset_id": 2}],
            )
            results = coll.query(query_embeddings=[[0.1, 0.2, 0.3]], n_results=1)
            assert results["ids"][0][0] == "1"
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_add_update_delete(self):
        """ChromaDB supports add, update, and delete operations."""
        import chromadb
        d = tempfile.mkdtemp()
        try:
            client = chromadb.PersistentClient(path=d)
            coll = client.get_or_create_collection("quickmedia_test")
            coll.add(ids=["1"], embeddings=[[1.0, 0.0]], metadatas=[{"asset_id": 1}])
            # Update
            coll.update(ids=["1"], embeddings=[[0.0, 1.0]])
            results = coll.get(ids=["1"], include=["embeddings"])
            assert results["embeddings"] is not None
            assert results["embeddings"][0].tolist() == [0.0, 1.0]
            # Delete
            coll.delete(ids=["1"])
            results = coll.get(ids=["1"])
            assert len(results["ids"]) == 0
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


class TestEmbeddingAnalyzer:
    def test_build_description_text(self):
        """_build_field_text description combines ai_description, summary, manual description."""
        from quickmedia.embedding import _build_field_text
        asset = {
            "filename": "vacation.jpg",
            "visual_description": "海边日落",
            "ai_summary": None,
            "tags": [{"name": "旅行"}, {"name": "海滩"}],
            "ocr_text": "",
            "transcript": None,
            "description": "我的假日照片",
        }
        text = _build_field_text(asset, "description")
        assert "海边日落" in text
        assert "我的假日照片" in text
        assert "None" not in text

    def test_build_tags_text(self):
        """_build_field_text tags combines tag names."""
        from quickmedia.embedding import _build_field_text
        asset = {"tags": [{"name": "旅行"}, {"name": "海滩"}]}
        text = _build_field_text(asset, "tags")
        assert "旅行" in text
        assert "海滩" in text

    def test_build_text_field(self):
        """_build_field_text text combines ocr_text, transcript and filename."""
        from quickmedia.embedding import _build_field_text
        asset = {"filename": "doc.pdf", "ocr_text": "Hello", "transcript": "speech here"}
        text = _build_field_text(asset, "text")
        assert "Hello" in text
        assert "speech here" in text
        assert "doc.pdf" in text
