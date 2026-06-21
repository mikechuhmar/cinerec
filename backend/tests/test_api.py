def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["movies"] == 5
    assert data["embeddings"] == 5
    assert data["embedder"] == "hash"


def test_list_and_search_movies(client):
    resp = client.get("/movies", params={"q": "matrix"})
    assert resp.status_code == 200
    titles = [m["title"] for m in resp.json()]
    assert "The Matrix" in titles

    resp = client.get("/movies", params={"genre": "Animation"})
    titles = [m["title"] for m in resp.json()]
    assert "Toy Story" in titles and "A Bug's Life" in titles


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


def test_add_rating_and_invalidate(client):
    resp = client.post("/ratings", json={"user_id": 3, "movie_id": 3, "rating": 5.0})
    assert resp.status_code == 201
    detail = client.get("/movies/3").json()
    assert detail["num_ratings"] == 2
