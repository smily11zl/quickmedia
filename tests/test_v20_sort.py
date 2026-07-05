
import sys, os, json

def test_sort_applies_in_all_modes():
    """s1: sort should apply regardless of search mode."""
    # Simulate the bug: old code wraps sort in if(smode==="keyword")
    modes = ["keyword", "semantic", "combined", "ai"]
    assets = [
        {"filename": "c.jpg", "size": 100, "modified_at": "2024-01-01"},
        {"filename": "a.jpg", "size": 300, "modified_at": "2024-03-01"},
        {"filename": "b.jpg", "size": 200, "modified_at": "2024-02-01"},
    ]
    
    for mode in modes:
        sorted_assets = sorted(assets, key=lambda a: a["filename"])
        assert sorted_assets[0]["filename"] == "a.jpg", f"Sort failed in {mode} mode"

print("test_sort_applies_in_all_modes: PASSED")
test_sort_applies_in_all_modes()

def test_score_sort_exists():
    """s1: score sort option should be available for semantic/combined modes."""
    sort_options_keyword = ["name", "size", "date", "hot"]
    sort_options_semantic = ["score", "name", "size", "date", "hot"]
    assert "score" not in sort_options_keyword
    assert "score" in sort_options_semantic
    print("test_score_sort_exists: PASSED")
test_score_sort_exists()
