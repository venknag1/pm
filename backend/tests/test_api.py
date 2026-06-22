"""Backend API tests. Each test gets a fresh isolated SQLite database."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestHealth:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestAuth:
    def test_login_success(self, client):
        resp = client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "user"
        assert "session" in client.cookies

    def test_login_wrong_password(self, client):
        resp = client.post(
            "/api/auth/login", json={"username": "user", "password": "wrong"}
        )
        assert resp.status_code == 401

    def test_login_wrong_username(self, client):
        resp = client.post(
            "/api/auth/login", json={"username": "admin", "password": "password"}
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 422

    def test_logout_clears_cookie(self, auth_client):
        resp = auth_client.post("/api/auth/logout")
        assert resp.status_code == 200
        assert "session" not in auth_client.cookies

    def test_me_authenticated(self, auth_client):
        resp = auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["username"] == "user"

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


class TestBoard:
    def test_get_board_unauthenticated(self, client):
        resp = client.get("/api/board")
        assert resp.status_code == 401

    def test_get_board_returns_five_columns(self, auth_client):
        resp = auth_client.get("/api/board")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["columns"]) == 5

    def test_get_board_column_titles(self, auth_client):
        resp = auth_client.get("/api/board")
        titles = [c["title"] for c in resp.json()["columns"]]
        assert titles == ["Backlog", "Discovery", "In Progress", "Review", "Done"]

    def test_get_board_starts_empty(self, auth_client):
        resp = auth_client.get("/api/board")
        data = resp.json()
        assert data["cards"] == {}
        assert all(col["cardIds"] == [] for col in data["columns"])


class TestColumns:
    def test_rename_column(self, auth_client):
        resp = auth_client.patch(
            "/api/columns/col-backlog", json={"title": "Icebox"}
        )
        assert resp.status_code == 200
        board = auth_client.get("/api/board").json()
        assert board["columns"][0]["title"] == "Icebox"

    def test_rename_column_not_found(self, auth_client):
        resp = auth_client.patch(
            "/api/columns/col-nonexistent", json={"title": "X"}
        )
        assert resp.status_code == 404

    def test_rename_column_empty_title_rejected(self, auth_client):
        resp = auth_client.patch("/api/columns/col-backlog", json={"title": ""})
        assert resp.status_code == 422

    def test_rename_column_unauthenticated(self, client):
        resp = client.patch("/api/columns/col-backlog", json={"title": "X"})
        assert resp.status_code == 401


class TestCards:
    def _create(self, client, column_id="col-backlog", title="Test card", details=""):
        resp = client.post(
            "/api/cards",
            json={"column_id": column_id, "title": title, "details": details},
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_create_card(self, auth_client):
        card_id = self._create(auth_client, title="My card", details="Some details")
        board = auth_client.get("/api/board").json()
        assert card_id in board["cards"]
        assert board["cards"][card_id]["title"] == "My card"
        assert board["cards"][card_id]["details"] == "Some details"
        assert card_id in board["columns"][0]["cardIds"]

    def test_create_card_appends_in_order(self, auth_client):
        id1 = self._create(auth_client, title="First")
        id2 = self._create(auth_client, title="Second")
        board = auth_client.get("/api/board").json()
        card_ids = board["columns"][0]["cardIds"]
        assert card_ids.index(id1) < card_ids.index(id2)

    def test_create_card_bad_column(self, auth_client):
        resp = auth_client.post(
            "/api/cards", json={"column_id": "col-nope", "title": "X"}
        )
        assert resp.status_code == 404

    def test_create_card_empty_title_rejected(self, auth_client):
        resp = auth_client.post(
            "/api/cards", json={"column_id": "col-backlog", "title": ""}
        )
        assert resp.status_code == 422

    def test_create_card_unauthenticated(self, client):
        resp = client.post(
            "/api/cards", json={"column_id": "col-backlog", "title": "X"}
        )
        assert resp.status_code == 401

    def test_update_card_title_and_details(self, auth_client):
        card_id = self._create(auth_client)
        resp = auth_client.patch(
            f"/api/cards/{card_id}",
            json={"title": "Updated", "details": "New details"},
        )
        assert resp.status_code == 200
        board = auth_client.get("/api/board").json()
        assert board["cards"][card_id]["title"] == "Updated"
        assert board["cards"][card_id]["details"] == "New details"

    def test_update_card_partial_title_only(self, auth_client):
        card_id = self._create(auth_client, title="Original", details="Keep me")
        auth_client.patch(f"/api/cards/{card_id}", json={"title": "Changed"})
        board = auth_client.get("/api/board").json()
        assert board["cards"][card_id]["title"] == "Changed"
        assert board["cards"][card_id]["details"] == "Keep me"

    def test_update_card_not_found(self, auth_client):
        resp = auth_client.patch("/api/cards/bad-id", json={"title": "X"})
        assert resp.status_code == 404

    def test_delete_card(self, auth_client):
        card_id = self._create(auth_client)
        resp = auth_client.delete(f"/api/cards/{card_id}")
        assert resp.status_code == 200
        board = auth_client.get("/api/board").json()
        assert card_id not in board["cards"]
        assert card_id not in board["columns"][0]["cardIds"]

    def test_delete_card_compacts_positions(self, auth_client):
        id1 = self._create(auth_client, title="A")
        id2 = self._create(auth_client, title="B")
        id3 = self._create(auth_client, title="C")
        auth_client.delete(f"/api/cards/{id2}")
        board = auth_client.get("/api/board").json()
        assert board["columns"][0]["cardIds"] == [id1, id3]

    def test_delete_card_not_found(self, auth_client):
        resp = auth_client.delete("/api/cards/bad-id")
        assert resp.status_code == 404

    def test_move_card_within_column(self, auth_client):
        id1 = self._create(auth_client, title="A")
        id2 = self._create(auth_client, title="B")
        id3 = self._create(auth_client, title="C")
        # Move id1 from position 0 to position 2 (end)
        resp = auth_client.patch(
            f"/api/cards/{id1}/move", json={"column_id": "col-backlog", "position": 2}
        )
        assert resp.status_code == 200
        board = auth_client.get("/api/board").json()
        assert board["columns"][0]["cardIds"] == [id2, id3, id1]

    def test_move_card_to_different_column(self, auth_client):
        card_id = self._create(auth_client, title="Move me")
        resp = auth_client.patch(
            f"/api/cards/{card_id}/move",
            json={"column_id": "col-done", "position": 0},
        )
        assert resp.status_code == 200
        board = auth_client.get("/api/board").json()
        assert card_id not in board["columns"][0]["cardIds"]
        done_col = next(c for c in board["columns"] if c["id"] == "col-done")
        assert card_id in done_col["cardIds"]

    def test_move_card_not_found(self, auth_client):
        resp = auth_client.patch(
            "/api/cards/bad-id/move", json={"column_id": "col-backlog", "position": 0}
        )
        assert resp.status_code == 404

    def test_move_card_bad_column(self, auth_client):
        card_id = self._create(auth_client)
        resp = auth_client.patch(
            f"/api/cards/{card_id}/move",
            json={"column_id": "col-nope", "position": 0},
        )
        assert resp.status_code == 404

    def test_move_card_unauthenticated(self, client):
        resp = client.patch(
            "/api/cards/any-id/move",
            json={"column_id": "col-backlog", "position": 0},
        )
        assert resp.status_code == 401


import json as _json


def _ai_response(reply: str = "Got it.", board_update=None) -> str:
    """Serialize a canned AI response as the JSON string the model would return."""
    return _json.dumps({"reply": reply, "board_update": board_update})


def _mock_openai(reply: str = "Got it.", board_update=None):
    """Return a context manager that patches AsyncOpenAI with a canned structured reply."""
    choice = MagicMock()
    choice.message.content = _ai_response(reply, board_update)
    completion = MagicMock()
    completion.choices = [choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=completion)

    return patch("backend.main.AsyncOpenAI", return_value=mock_client)


def _make_card(auth_client, column_id: str = "col-backlog", title: str = "Test card") -> str:
    resp = auth_client.post("/api/cards", json={"column_id": column_id, "title": title})
    assert resp.status_code == 201
    return resp.json()["id"]


class TestAI:
    def test_ai_unauthenticated(self, client):
        resp = client.post("/api/ai", json={"message": "2+2"})
        assert resp.status_code == 401

    def test_ai_missing_key(self, auth_client, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        resp = auth_client.post("/api/ai", json={"message": "2+2"})
        assert resp.status_code == 503

    def test_ai_empty_message(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        resp = auth_client.post("/api/ai", json={"message": ""})
        assert resp.status_code == 422

    def test_ai_returns_reply_no_board_changes(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with _mock_openai("The answer is 4.", board_update=None):
            resp = auth_client.post("/api/ai", json={"message": "What is 2+2?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["reply"] == "The answer is 4."
        assert body["board"] is None

    def test_ai_sends_board_context_in_system_message(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        _make_card(auth_client, title="Context card")
        with _mock_openai() as mock_cls:
            auth_client.post("/api/ai", json={"message": "hi"})
        messages = mock_cls.return_value.chat.completions.create.call_args.kwargs["messages"]
        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert "Context card" in system_msg["content"]
        assert "col-backlog" in system_msg["content"]

    def test_ai_sends_user_message_last(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with _mock_openai() as mock_cls:
            auth_client.post("/api/ai", json={"message": "hello there"})
        messages = mock_cls.return_value.chat.completions.create.call_args.kwargs["messages"]
        assert messages[-1] == {"role": "user", "content": "hello there"}

    def test_ai_includes_history_in_messages(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        history = [
            {"role": "user", "content": "first message"},
            {"role": "assistant", "content": "first reply"},
        ]
        with _mock_openai() as mock_cls:
            auth_client.post("/api/ai", json={"message": "second message", "history": history})
        messages = mock_cls.return_value.chat.completions.create.call_args.kwargs["messages"]
        # system, history[0], history[1], current
        assert len(messages) == 4
        assert messages[1] == {"role": "user", "content": "first message"}
        assert messages[2] == {"role": "assistant", "content": "first reply"}
        assert messages[3] == {"role": "user", "content": "second message"}

    def test_ai_calls_correct_model(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with _mock_openai() as mock_cls:
            auth_client.post("/api/ai", json={"message": "hi"})
        call_kwargs = mock_cls.return_value.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "meta-llama/llama-3.3-70b-instruct"
        assert "response_format" not in call_kwargs

    def test_ai_creates_card_via_board_update(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        update = {"create_cards": [{"column_id": "col-backlog", "title": "AI card", "details": "added by AI"}]}
        with _mock_openai("Done, I added the card.", board_update=update):
            resp = auth_client.post("/api/ai", json={"message": "add a card"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["reply"] == "Done, I added the card."
        assert body["board"] is not None
        backlog = next(c for c in body["board"]["columns"] if c["id"] == "col-backlog")
        card_ids = backlog["cardIds"]
        titles = [body["board"]["cards"][cid]["title"] for cid in card_ids]
        assert "AI card" in titles

    def test_ai_deletes_card_via_board_update(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        card_id = _make_card(auth_client, title="To delete")
        update = {"delete_card_ids": [card_id]}
        with _mock_openai("Deleted.", board_update=update):
            resp = auth_client.post("/api/ai", json={"message": "delete that card"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["board"] is not None
        assert card_id not in body["board"]["cards"]

    def test_ai_moves_card_via_board_update(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        card_id = _make_card(auth_client, column_id="col-backlog", title="To move")
        update = {"move_cards": [{"card_id": card_id, "column_id": "col-done", "position": 0}]}
        with _mock_openai("Moved.", board_update=update):
            resp = auth_client.post("/api/ai", json={"message": "move it to done"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["board"] is not None
        done_col = next(c for c in body["board"]["columns"] if c["id"] == "col-done")
        assert card_id in done_col["cardIds"]

    def test_ai_renames_column_via_board_update(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        update = {"rename_columns": [{"column_id": "col-backlog", "title": "Queue"}]}
        with _mock_openai("Renamed.", board_update=update):
            resp = auth_client.post("/api/ai", json={"message": "rename backlog to queue"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["board"] is not None
        backlog = next(c for c in body["board"]["columns"] if c["id"] == "col-backlog")
        assert backlog["title"] == "Queue"

    def test_ai_ignores_invalid_card_ids_in_update(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        update = {"delete_card_ids": ["card-does-not-exist"]}
        with _mock_openai("Done.", board_update=update):
            resp = auth_client.post("/api/ai", json={"message": "delete it"})
        assert resp.status_code == 200
        # No DB changes → board is None
        assert resp.json()["board"] is None

    def test_ai_handles_malformed_json_response(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        choice = MagicMock()
        choice.message.content = "not json at all"
        completion = MagicMock()
        completion.choices = [choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=completion)
        with patch("backend.main.AsyncOpenAI", return_value=mock_client):
            resp = auth_client.post("/api/ai", json={"message": "hi"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["reply"] == "not json at all"
        assert body["board"] is None
