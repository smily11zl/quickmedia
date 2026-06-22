"""Embedding adapter and ChromaDB management for QuickMedia."""

import json
import os
import urllib.request
from collections import defaultdict


def top_k_aggregate(per_asset_dists: dict[int, list[float]], k: int = 2) -> dict[int, float]:
    """Aggregate per-search-term distances with Top-K averaging.
    
    For each asset, takes the k smallest distances and averages them.
    Assets with fewer than k terms use all available.
    """
    result = {}
    for asset_id, dists in per_asset_dists.items():
        if not dists:
            continue
        top = sorted(dists)[:k]
        result[asset_id] = sum(top) / len(top)
    return result

# Field weights for semantic search
DEFAULT_FIELD_WEIGHTS = {"description": 0.5, "tags": 0.3, "text": 0.2}


def _build_field_text(asset: dict, field: str) -> str:
    """Build embedding text for a specific field."""
    if field == "description":
        parts = []
        atype = asset.get("asset_type", "")
        # Video: prefer video_summary, fall back to visual_description
        if atype == "video":
            if asset.get("video_summary"):
                parts.append(str(asset["video_summary"]))
            elif asset.get("visual_description"):
                parts.append(str(asset["visual_description"]))
        else:
            if asset.get("visual_description"):
                parts.append(str(asset["visual_description"]))
        if asset.get("ai_summary"):
            parts.append(str(asset["ai_summary"]))
        if asset.get("description"):
            parts.append(str(asset["description"]))
        return "\n".join(parts) if parts else str(asset.get("filename", ""))
    elif field == "tags":
        tags = asset.get("tags", [])
        if not tags:
            return ""
        if isinstance(tags[0], dict):
            return " ".join(t.get("name", "") for t in tags if t.get("name"))
        return " ".join(str(t) for t in tags)
    elif field == "text":
        parts = []
        if asset.get("ocr_text"):
            parts.append(str(asset["ocr_text"]))
        if asset.get("transcript"):
            parts.append(str(asset["transcript"]))
        if asset.get("filename"):
            parts.append(str(asset["filename"]))
        return "\n".join(parts) if parts else ""
    return ""


class EmbeddingAdapter:
    """Adapter for Ollama's embedding API."""

    def __init__(self, base_url: str, model: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        """Embed text and return a vector (list of floats)."""
        url = f"{self.base_url}/api/embed"
        body = json.dumps({"model": self.model, "input": text}).encode("utf-8")
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", "application/json")
        print(f"[Embedding] model={self.model}", flush=True)
        print(f"[Embedding input] {text[:300]}", flush=True)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            vector = data["embeddings"][0]
            print(f"[Embedding output] dim={len(vector)} first_5={vector[:5]}", flush=True)
            return vector


class OpenAiEmbeddingAdapter:
    """Adapter for OpenAI-compatible embedding API (/v1/embeddings)."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        """Embed text via /v1/embeddings and return a vector."""
        url = f"{self.base_url}/embeddings"
        body = json.dumps({"model": self.model, "input": text}).encode("utf-8")
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        print(f"[Embedding] model={self.model}", flush=True)
        print(f"[Embedding input] {text[:300]}", flush=True)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            vector = data["data"][0]["embedding"]
            print(f"[Embedding output] dim={len(vector)} first_5={vector[:5]}", flush=True)
            return vector


class ChromaStore:
    """Manages the ChromaDB collection for per-field asset embeddings."""

    def __init__(self, persist_path: str):
        import chromadb
        self._client = chromadb.PersistentClient(path=persist_path)
        self._collection = self._client.get_or_create_collection("quickmedia_assets")

    def _id(self, asset_id: int, field: str) -> str:
        return f"{field}_{asset_id}"

    def add(self, asset_id: int, field: str, vector: list[float], term_index: int = None, term_text: str = None) -> None:
        """Add or update a field's embedding for an asset."""
        if term_index is not None:
            sid = f"search_{asset_id}_{term_index}"
        else:
            sid = self._id(asset_id, field)
        metadata = {"asset_id": asset_id, "field": field if term_index is None else "search"}
        if term_text:
            metadata["term"] = term_text
        existing = self._collection.get(ids=[sid])
        if existing and existing["ids"]:
            self._collection.update(ids=[sid], embeddings=[vector])
        else:
            self._collection.add(ids=[sid], embeddings=[vector], metadatas=[metadata])

    def add_fields(self, asset_id: int, vectors: dict[str, list[float]]) -> None:
        """Add embeddings for multiple fields at once."""
        for field, vector in vectors.items():
            if vector:
                self.add(asset_id, field, vector)

    def delete(self, asset_id: int) -> None:
        """Remove all field and search embeddings for an asset."""
        # Old format fields
        for field in ("description", "tags", "text"):
            self._collection.delete(ids=[self._id(asset_id, field)])
        # Search term vectors: delete all matching prefix
        all_ids = self._collection.get()["ids"]
        to_delete = [sid for sid in all_ids if sid.startswith(f"search_{asset_id}_")]
        if to_delete:
            self._collection.delete(ids=to_delete)

    def query(self, query_vector: list[float], n_results: int = 10) -> list[dict]:
        """Query similar assets using single vector (backward compat). Returns list of {asset_id, distance}."""
        return self._raw_query(query_vector, n_results)

    def query_weighted(self, query_vector: list[float], weights: dict[str, float] = None,
                       n_results: int = 10) -> list[dict]:
        """Query using per-field weighted merge. Each field is queried separately,
        then results are merged by weighted distance."""
        weights = weights or DEFAULT_FIELD_WEIGHTS
        # Collect per-field results
        field_results: dict[int, list[float]] = defaultdict(list)
        for field, weight in weights.items():
            if weight <= 0:
                continue
            results = self._raw_query(query_vector, n_results * 2, field_filter=field)
            for item in results:
                asset_id = item["asset_id"]
                field_results[asset_id].append(item["distance"])

        # Merge: best-field (minimum distance across fields)
        merged = []
        for asset_id, dists in field_results.items():
            best_dist = min(dists) if dists else 0
            merged.append({"asset_id": asset_id, "distance": best_dist})

        merged.sort(key=lambda x: x["distance"])
        return merged[:n_results]

    def query_search_terms(self, query_vector: list[float], k: int = 2, n_results: int = 50) -> list[dict]:
        """Query against all search_term vectors with Top-K aggregation.
        
        Returns dicts with: asset_id, distance, top_k_details (list of {term_index, distance})
        """
        results = self._collection.query(query_embeddings=[query_vector], n_results=n_results * 10)
        if not results or not results["ids"] or not results["ids"][0]:
            return []
        
        per_asset: dict[int, list[tuple[int, float, str]]] = defaultdict(list)
        for i, sid in enumerate(results["ids"][0]):
            dist = results["distances"][0][i] if results.get("distances") else 0
            if "_" not in sid:
                continue
            field, rest = sid.split("_", 1)
            if field != "search":
                continue
            parts = rest.split("_")
            if len(parts) < 2:
                aid, tidx = int(parts[0]), 0
            else:
                aid, tidx = int(parts[0]), int(parts[1])
            term_name = ""
            metadatas = results.get("metadatas")
            if metadatas and metadatas[0] and i < len(metadatas[0]) and metadatas[0][i]:
                term_name = metadatas[0][i].get("term", "")
            per_asset[aid].append((tidx, dist, term_name))
        
        merged = []
        seen = set()
        for aid, pairs in per_asset.items():
            if aid in seen:
                continue
            seen.add(aid)
            pairs.sort(key=lambda x: x[1])
            top = pairs[:k]
            avg = sum(d for _, d, _ in top) / len(top)
            merged.append({
                "asset_id": aid,
                "distance": avg,
                "top_k_details": [{"term_index": idx, "distance": d, "term_name": tn} for idx, d, tn in top],
            })
        merged.sort(key=lambda x: x["distance"])
        return merged[:n_results]

    def _raw_query(self, query_vector: list[float], n_results: int, field_filter: str = None) -> list[dict]:
        """Low-level ChromaDB query, optionally filtered by field."""
        results = self._collection.query(query_embeddings=[query_vector], n_results=n_results)
        if not results or not results["ids"] or not results["ids"][0]:
            return []
        items = []
        for i, sid in enumerate(results["ids"][0]):
            if field_filter and not sid.startswith(field_filter + "_"):
                continue
            dist = results["distances"][0][i] if results.get("distances") else 0
            aid = int(sid.split("_", 1)[1]) if "_" in sid else int(sid)
            items.append({"asset_id": aid, "distance": dist})
        return items

    def get_vector(self, asset_id: int, field: str = "description", term_index: int = None) -> list[float] | None:
        """Get the embedding vector for a field of an asset."""
        if term_index is not None:
            sid = f"search_{asset_id}_{term_index}"
        else:
            sid = self._id(asset_id, field)
        result = self._collection.get(ids=[sid], include=["embeddings"])
        if result and result.get("embeddings") is not None and len(result["embeddings"]) > 0:
            return list(result["embeddings"][0])
        return None
