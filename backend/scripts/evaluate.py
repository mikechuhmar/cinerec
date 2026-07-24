"""Offline evaluation of the recommenders with leave-one-out HR@K and NDCG@K.

For each sampled user, one highly-rated movie is held out as the test item; models are
fit/scored using only the remaining (training) ratings. We then check whether the held-out
item appears in each method's top-K recommendations.

    uv run python -m scripts.evaluate --k 10 --users 300
    CINEREC_EMBEDDER=hash uv run python -m scripts.evaluate   # offline embedder
"""

from __future__ import annotations

import argparse

import numpy as np
import scipy.sparse as sp
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Movie, Rating


def _load(db) -> tuple[list[int], np.ndarray, dict[int, int], list[tuple[int, int, float]]]:
    rows = db.execute(select(Movie.id, Movie.embedding).where(Movie.embedding.is_not(None))).all()
    item_ids = [r[0] for r in rows]
    embeddings = np.array([r[1] for r in rows], dtype=np.float32)
    item_index = {mid: i for i, mid in enumerate(item_ids)}
    ratings = [
        (int(u), int(m), float(r))
        for u, m, r in db.execute(select(Rating.user_id, Rating.movie_id, Rating.rating)).all()
        if int(m) in item_index
    ]
    return item_ids, embeddings, item_index, ratings


def _metrics(rank: int | None, k: int) -> tuple[float, float]:
    """Return (hit@k, ndcg@k) for a held-out item at 0-based ``rank`` (or None if not in top-k)."""
    if rank is None or rank >= k:
        return 0.0, 0.0
    return 1.0, 1.0 / np.log2(rank + 2)


def evaluate(k: int, n_users: int, like_threshold: float, seed: int) -> None:
    rng = np.random.default_rng(seed)
    settings = get_settings()

    with SessionLocal() as db:
        item_ids, embeddings, item_index, ratings = _load(db)

    if not item_ids:
        print("No embeddings found. Run scripts.load_data and scripts.build_embeddings first.")
        return

    n_items = len(item_ids)
    by_user: dict[int, list[tuple[int, float]]] = {}
    for u, m, r in ratings:
        by_user.setdefault(u, []).append((item_index[m], r))

    # Eligible users: enough history and at least one liked item to hold out.
    eligible = [
        u
        for u, items in by_user.items()
        if len(items) >= 5 and any(r >= like_threshold for _, r in items)
    ]
    rng.shuffle(eligible)
    eligible = eligible[:n_users]
    print(f"Evaluating {len(eligible)} users · {n_items} items · K={k} · embedder={settings.embedder}")

    # Build train interactions (all eligible users' ratings minus their held-out item).
    test_item: dict[int, int] = {}
    train_rows, train_cols, train_vals = [], [], []
    user_index = {u: i for i, u in enumerate(eligible)}
    for u in eligible:
        items = by_user[u]
        liked = [iidx for iidx, r in items if r >= like_threshold]
        held = int(rng.choice(liked))
        test_item[u] = held
        for iidx, r in items:
            if iidx == held:
                continue
            train_rows.append(user_index[u])
            train_cols.append(iidx)
            train_vals.append(r)

    train = sp.csr_matrix(
        (train_vals, (train_rows, train_cols)), shape=(len(eligible), n_items)
    )

    from implicit.als import AlternatingLeastSquares

    als = AlternatingLeastSquares(
        factors=settings.als_factors,
        iterations=settings.als_iterations,
        regularization=settings.als_regularization,
        random_state=seed,
    )
    als.fit(train, show_progress=False)

    results = {m: {"hr": [], "ndcg": []} for m in ("content", "collaborative", "hybrid")}

    def ranked(scores: np.ndarray, seen: set[int], target: int) -> int | None:
        scores = scores.copy()
        if seen:
            scores[list(seen)] = -np.inf
        top = np.argpartition(-scores, min(k, n_items - 1))[:k]
        top = top[np.argsort(-scores[top])]
        hits = np.where(top == target)[0]
        return int(hits[0]) if len(hits) else None

    for u in eligible:
        uidx = user_index[u]
        seen = {iidx for iidx, _ in by_user[u] if iidx != test_item[u]}
        target = test_item[u]

        liked_idx = [iidx for iidx, r in by_user[u] if r >= like_threshold and iidx != target]
        if liked_idx:
            profile = embeddings[liked_idx].mean(axis=0)
            norm = np.linalg.norm(profile)
            profile = profile / norm if norm else profile
        else:
            profile = np.zeros(embeddings.shape[1], dtype=np.float32)
        content_scores = embeddings @ profile

        cf_scores = als.user_factors[uidx] @ als.item_factors.T
        cf_scores = np.asarray(cf_scores).ravel()[:n_items]

        def _norm(x: np.ndarray) -> np.ndarray:
            lo, hi = x.min(), x.max()
            return (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x)

        hybrid_scores = 0.5 * _norm(cf_scores) + 0.5 * _norm(content_scores)

        for name, scores in (
            ("content", content_scores),
            ("collaborative", cf_scores),
            ("hybrid", hybrid_scores),
        ):
            hr, ndcg = _metrics(ranked(scores, seen, target), k)
            results[name]["hr"].append(hr)
            results[name]["ndcg"].append(ndcg)

    print(f"\n{'method':<16}{'HR@'+str(k):>10}{'NDCG@'+str(k):>12}")
    print("-" * 38)
    for name, vals in results.items():
        print(f"{name:<16}{np.mean(vals['hr']):>10.4f}{np.mean(vals['ndcg']):>12.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline evaluation of cinerec recommenders")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--users", type=int, default=300)
    parser.add_argument("--like-threshold", type=float, default=4.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    evaluate(args.k, args.users, args.like_threshold, args.seed)


if __name__ == "__main__":
    main()
