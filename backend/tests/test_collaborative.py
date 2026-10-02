"""Tests for ALS model persistence and (re)training behaviour."""

import os

import numpy as np

from app.config import get_settings
from app.db import SessionLocal
from app.recsys import collaborative


def test_als_persistence_roundtrip(client, tmp_path, monkeypatch):
    """A trained model saved to disk warm-loads back with identical factors/indexes."""
    path = str(tmp_path / "model.npz")
    monkeypatch.setattr(get_settings(), "als_model_path", path)

    collaborative.reset()
    with SessionLocal() as db:
        state = collaborative._train(db)
    assert state.model is not None

    collaborative._save_model(state)
    assert os.path.exists(path)

    loaded = collaborative._load_model()
    assert loaded is not None
    assert loaded.item_index == state.item_index
    assert loaded.user_index == state.user_index
    assert np.allclose(loaded.model.item_factors, state.model.item_factors)
    assert np.allclose(loaded.model.user_factors, state.model.user_factors)


def test_als_load_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(get_settings(), "als_model_path", "")
    assert collaborative._load_model() is None


def test_retrain_once_updates_state_and_counts(client, monkeypatch):
    """A direct retrain rebuilds the in-memory state and bumps the metrics counter."""
    monkeypatch.setattr(get_settings(), "als_model_path", "")
    collaborative.reset()

    from app.observability import ALS_RETRAINS

    before = ALS_RETRAINS.labels(trigger="unit")._value.get()
    collaborative._retrain_once(trigger="unit")
    after = ALS_RETRAINS.labels(trigger="unit")._value.get()

    status = collaborative.status()
    assert status["trained"] is True
    assert status["users"] > 0
    assert after == before + 1


def test_invalidate_sync_mode_resets_model(client):
    """With background retraining off (test config), invalidate drops the cached model."""
    with SessionLocal() as db:
        collaborative.get_state(db)
    assert collaborative._model_state is not None

    collaborative.invalidate()
    assert collaborative._model_state is None
