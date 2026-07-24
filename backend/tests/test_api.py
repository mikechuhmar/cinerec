def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["movies"] == 5
    assert data["embeddings"] == 5
    assert data["embedder"] == "hash"
    assert data["cache_backend"] == "in-process"
    assert data["als"]["background_retrain"] is False


def test_list_and_search_movies(client):
    resp = client.get("/movies", params={"q": "matrix"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    titles = [m["title"] for m in body["items"]]
    assert "The Matrix" in titles

    resp = client.get("/movies", params={"genre": "Animation"})
    titles = [m["title"] for m in resp.json()["items"]]
    assert "Toy Story" in titles and "A Bug's Life" in titles


def test_list_filters_and_pagination(client):
    # Year filter.
    body = client.get("/movies", params={"year_from": 1998, "year_to": 2000}).json()
    years = [m["year"] for m in body["items"]]
    assert years and all(1998 <= y <= 2000 for y in years)

    # min_rating filter (A Bug's Life avg = 4.5, Pride & Prejudice avg = 2.0).
    body = client.get("/movies", params={"min_rating": 4.0}).json()
    titles = [m["title"] for m in body["items"]]
    assert "A Bug's Life" in titles and "Pride and Prejudice" not in titles

    # Pagination metadata.
    page = client.get("/movies", params={"limit": 2, "offset": 0}).json()
    assert page["limit"] == 2 and len(page["items"]) == 2 and page["total"] == 5


def test_list_genres(client):
    genres = client.get("/movies/genres").json()
    assert "Animation" in genres and "Sci-Fi" in genres
    assert genres == sorted(genres)


def test_movie_detail_with_ratings(client):
    resp = client.get("/movies/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Toy Story"
    assert data["num_ratings"] == 2
    assert data["avg_rating"] is not None


def test_movie_not_found(client):
    assert client.get("/movies/9999").status_code == 404


def test_content_similarity(client):
    # The Matrix (sci-fi action) should be most similar to Terminator 2.
    resp = client.get("/recommend/similar/3", params={"method": "content"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "content"
    assert data["items"], "expected non-empty recommendations"
    assert data["items"][0]["title"] == "Terminator 2"


def test_collaborative_user_recommendation(client):
    # User 1 likes animated kids films; A Bug's Life is rated, Toy Story too,
    # so CF should surface unseen items influenced by similar users.
    resp = client.get("/recommend/user/1", params={"method": "collaborative"})
    assert resp.status_code == 200
    assert resp.json()["source"] == "collaborative"


def test_content_user_recommendation(client):
    resp = client.get("/recommend/user/2", params={"method": "content"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "content"
    # User 2 likes sci-fi; recommendations should exclude already-rated movies.
    rec_ids = {item["id"] for item in data["items"]}
    assert 3 not in rec_ids and 4 not in rec_ids


def test_hybrid_similarity(client):
    resp = client.get("/recommend/similar/3", params={"method": "hybrid", "alpha": 0.5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "hybrid"
    assert data["items"], "expected non-empty hybrid recommendations"


def test_hybrid_user_recommendation(client):
    resp = client.get("/recommend/user/1", params={"method": "hybrid"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "hybrid"
    # Already-rated movies must be excluded from the user's recommendations.
    rec_ids = {item["id"] for item in data["items"]}
    assert 1 not in rec_ids and 2 not in rec_ids


def test_recommendation_cache(client):
    from app.recsys import cache

    cache.clear()
    key = "similar:3:content:10:0.5"
    assert cache.get(key) is None

    first = client.get("/recommend/similar/3", params={"method": "content"}).json()
    # The response is now cached and identical on a second call.
    assert cache.get(key) is not None
    second = client.get("/recommend/similar/3", params={"method": "content"}).json()
    assert first == second

    # New ratings invalidate (clear) the recommendation cache.
    client.post("/ratings", json={"user_id": 7, "movie_id": 3, "rating": 5.0})
    assert cache.get(key) is None


def test_add_rating_and_invalidate(client):
    resp = client.post("/ratings", json={"user_id": 3, "movie_id": 3, "rating": 5.0})
    assert resp.status_code == 201
    detail = client.get("/movies/3").json()
    assert detail["num_ratings"] == 2
