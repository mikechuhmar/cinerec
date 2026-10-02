"""Unit tests for the recommendation blending/normalisation helpers (no DB)."""

from app.recsys.content import build_movie_text
from app.recsys.hybrid import _blend, _normalize


class _M:
    def __init__(self, i: int) -> None:
        self.id = i


def test_normalize_scales_to_unit_interval():
    out = _normalize([(_M(1), 2.0), (_M(2), 4.0), (_M(3), 6.0)])
    assert out[1][1] == 0.0
    assert out[2][1] == 0.5
    assert out[3][1] == 1.0


def test_normalize_single_item_is_one():
    out = _normalize([(_M(1), 5.0)])
    assert out[1][1] == 1.0


def test_normalize_empty():
    assert _normalize([]) == {}


def test_blend_weights_sources_by_alpha():
    content = [(_M(1), 10.0), (_M(2), 0.0)]  # normalised: m1=1, m2=0
    cf = [(_M(1), 0.0), (_M(3), 10.0)]  # normalised: m1=0, m3=1
    result = {m.id: round(s, 4) for m, s in _blend(content, cf, alpha=0.5, limit=10)}
    assert result[1] == 0.5  # 0.5*0 + 0.5*1
    assert result[3] == 0.5  # 0.5*1 + 0.5*0
    assert result[2] == 0.0


def test_blend_alpha_one_is_pure_collaborative():
    content = [(_M(1), 10.0)]
    cf = [(_M(2), 10.0)]
    result = {m.id: s for m, s in _blend(content, cf, alpha=1.0, limit=10)}
    assert result[2] == 1.0
    assert result[1] == 0.0


def test_blend_respects_limit():
    content = [(_M(i), float(i)) for i in range(10)]
    assert len(_blend(content, [], alpha=0.0, limit=3)) == 3


def test_build_movie_text_includes_all_parts():
    text = build_movie_text("Toy Story", 1995, ["Animation", "Comedy"], "toys", "a cowboy doll")
    for part in ("Toy Story", "1995", "Animation", "Comedy", "toys", "a cowboy doll"):
        assert part in text


def test_build_movie_text_handles_missing_fields():
    text = build_movie_text("Solo", None, [], None, None)
    assert text == "Solo"
