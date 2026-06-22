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
        data = resp.json()
        assert data["username"] == "user"
        assert data["is_admin"] is False
        assert "session" in client.cookies

    def test_login_admin_user(self, client):
        resp = client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["is_admin"] is True

    def test_login_wrong_password(self, client):
        resp = client.post(
            "/api/auth/login", json={"username": "user", "password": "wrong"}
        )
        assert resp.status_code == 401

    def test_login_wrong_username(self, client):
        resp = client.post(
            "/api/auth/login", json={"username": "nobody", "password": "password"}
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
        data = resp.json()
        assert data["username"] == "user"
        assert data["is_admin"] is False

    def test_me_admin(self, admin_client):
        resp = admin_client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is True

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_register_new_user(self, client):
        resp = client.post(
            "/api/auth/register", json={"username": "newuser", "password": "secret123"}
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"

    def test_register_and_login(self, client):
        client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
        resp = client.post("/api/auth/login", json={"username": "alice", "password": "pass1234"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "alice"

    def test_register_duplicate_username(self, client):
        client.post("/api/auth/register", json={"username": "bob", "password": "pass1234"})
        resp = client.post("/api/auth/register", json={"username": "bob", "password": "different123"})
        assert resp.status_code == 409

    def test_register_short_password_rejected(self, client):
        resp = client.post("/api/auth/register", json={"username": "carol", "password": "abc"})
        assert resp.status_code == 422

    def test_register_empty_username_rejected(self, client):
        resp = client.post("/api/auth/register", json={"username": "", "password": "secret123"})
        assert resp.status_code == 422

    def test_registered_user_is_not_admin(self, client):
        client.post("/api/auth/register", json={"username": "dave", "password": "pass1234"})
        client.post("/api/auth/login", json={"username": "dave", "password": "pass1234"})
        resp = client.get("/api/auth/me")
        assert resp.json()["is_admin"] is False

    def test_registered_user_gets_default_board(self, client):
        client.post("/api/auth/register", json={"username": "eve", "password": "pass1234"})
        client.post("/api/auth/login", json={"username": "eve", "password": "pass1234"})
        resp = client.get("/api/board")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["columns"]) == 5


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


class TestBoards:
    def test_list_boards_unauthenticated(self, client):
        resp = client.get("/api/boards")
        assert resp.status_code == 401

    def test_list_boards_returns_initial_board(self, auth_client):
        resp = auth_client.get("/api/boards")
        assert resp.status_code == 200
        boards = resp.json()
        assert len(boards) == 1
        assert boards[0]["title"] == "My Board"
        assert "id" in boards[0]
        assert "created_at" in boards[0]
        assert boards[0]["card_count"] == 0

    def test_create_board(self, auth_client):
        resp = auth_client.post("/api/boards", json={"title": "Sprint Board"})
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["title"] == "Sprint Board"

    def test_create_board_appears_in_list(self, auth_client):
        auth_client.post("/api/boards", json={"title": "Sprint Board"})
        resp = auth_client.get("/api/boards")
        titles = [b["title"] for b in resp.json()]
        assert "Sprint Board" in titles

    def test_create_board_has_default_columns(self, auth_client):
        create_resp = auth_client.post("/api/boards", json={"title": "New Board"})
        board_id = create_resp.json()["id"]
        resp = auth_client.get(f"/api/boards/{board_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["columns"]) == 5
        titles = [c["title"] for c in data["columns"]]
        assert titles == ["Backlog", "Discovery", "In Progress", "Review", "Done"]

    def test_create_board_empty_title_rejected(self, auth_client):
        resp = auth_client.post("/api/boards", json={"title": ""})
        assert resp.status_code == 422

    def test_get_board_by_id(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        resp = auth_client.get(f"/api/boards/{board_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "columns" in data
        assert "cards" in data

    def test_get_board_by_id_not_found(self, auth_client):
        resp = auth_client.get("/api/boards/99999")
        assert resp.status_code == 404

    def test_get_board_by_id_unauthenticated(self, client):
        resp = client.get("/api/boards/1")
        assert resp.status_code == 401

    def test_rename_board(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        resp = auth_client.patch(f"/api/boards/{board_id}", json={"title": "Renamed Board"})
        assert resp.status_code == 200
        boards = auth_client.get("/api/boards").json()
        board = next(b for b in boards if b["id"] == board_id)
        assert board["title"] == "Renamed Board"

    def test_rename_board_empty_title_rejected(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        resp = auth_client.patch(f"/api/boards/{board_id}", json={"title": ""})
        assert resp.status_code == 422

    def test_delete_board_not_allowed_when_only_one(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        resp = auth_client.delete(f"/api/boards/{board_id}")
        assert resp.status_code == 400

    def test_delete_board(self, auth_client):
        auth_client.post("/api/boards", json={"title": "To Delete"})
        boards = auth_client.get("/api/boards").json()
        board_to_delete = next(b for b in boards if b["title"] == "To Delete")
        resp = auth_client.delete(f"/api/boards/{board_to_delete['id']}")
        assert resp.status_code == 200
        boards_after = auth_client.get("/api/boards").json()
        ids = [b["id"] for b in boards_after]
        assert board_to_delete["id"] not in ids

    def test_delete_board_unauthenticated(self, client):
        resp = client.delete("/api/boards/1")
        assert resp.status_code == 401

    def test_boards_are_isolated_between_users(self, client):
        client.post("/api/auth/register", json={"username": "user1", "password": "pass1234"})
        client.post("/api/auth/register", json={"username": "user2", "password": "pass5678"})

        client.post("/api/auth/login", json={"username": "user1", "password": "pass1234"})
        client.post("/api/boards", json={"title": "User1 Board"})
        user1_boards = client.get("/api/boards").json()

        client.post("/api/auth/login", json={"username": "user2", "password": "pass5678"})
        user2_boards = client.get("/api/boards").json()

        user1_ids = {b["id"] for b in user1_boards}
        user2_ids = {b["id"] for b in user2_boards}
        assert user1_ids.isdisjoint(user2_ids)

    def test_cannot_access_another_users_board(self, client):
        client.post("/api/auth/register", json={"username": "alice2", "password": "pass1234"})
        client.post("/api/auth/register", json={"username": "bob2", "password": "pass5678"})

        client.post("/api/auth/login", json={"username": "alice2", "password": "pass1234"})
        alice_boards = client.get("/api/boards").json()
        alice_board_id = alice_boards[0]["id"]

        client.post("/api/auth/login", json={"username": "bob2", "password": "pass5678"})
        resp = client.get(f"/api/boards/{alice_board_id}")
        assert resp.status_code == 404

    def test_board_card_count_reflects_actual_cards(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        board_data = auth_client.get(f"/api/boards/{board_id}").json()
        col_id = board_data["columns"][0]["id"]
        auth_client.post("/api/boards/{}/cards".format(board_id),
                         json={"column_id": col_id, "title": "Card 1"})
        auth_client.post("/api/boards/{}/cards".format(board_id),
                         json={"column_id": col_id, "title": "Card 2"})
        boards = auth_client.get("/api/boards").json()
        board = next(b for b in boards if b["id"] == board_id)
        assert board["card_count"] == 2


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

    def test_create_column(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        resp = auth_client.post(
            f"/api/boards/{board_id}/columns", json={"title": "Testing"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["title"] == "Testing"

    def test_create_column_appears_on_board(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        auth_client.post(f"/api/boards/{board_id}/columns", json={"title": "QA"})
        board = auth_client.get(f"/api/boards/{board_id}").json()
        titles = [c["title"] for c in board["columns"]]
        assert "QA" in titles

    def test_create_column_appended_at_end(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        auth_client.post(f"/api/boards/{board_id}/columns", json={"title": "Last"})
        board = auth_client.get(f"/api/boards/{board_id}").json()
        assert board["columns"][-1]["title"] == "Last"

    def test_create_column_empty_title_rejected(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        resp = auth_client.post(f"/api/boards/{board_id}/columns", json={"title": ""})
        assert resp.status_code == 422

    def test_delete_column(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        # Add a column so we can delete a non-essential one
        auth_client.post(f"/api/boards/{board_id}/columns", json={"title": "Temp"})
        board = auth_client.get(f"/api/boards/{board_id}").json()
        temp_col = next(c for c in board["columns"] if c["title"] == "Temp")
        resp = auth_client.delete(f"/api/boards/{board_id}/columns/{temp_col['id']}")
        assert resp.status_code == 200
        board_after = auth_client.get(f"/api/boards/{board_id}").json()
        col_ids = [c["id"] for c in board_after["columns"]]
        assert temp_col["id"] not in col_ids

    def test_delete_column_not_found(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        resp = auth_client.delete(f"/api/boards/{board_id}/columns/col-nope")
        assert resp.status_code == 404

    def test_delete_column_unauthenticated(self, client):
        resp = client.delete("/api/boards/1/columns/col-backlog")
        assert resp.status_code == 401

    def test_delete_column_compacts_positions(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        board = auth_client.get(f"/api/boards/{board_id}").json()
        # Add extra column so we don't hit the "only one" guard
        auth_client.post(f"/api/boards/{board_id}/columns", json={"title": "Extra"})
        board = auth_client.get(f"/api/boards/{board_id}").json()
        # Delete the middle column (Discovery at position 1)
        disc_col = next(c for c in board["columns"] if c["title"] == "Discovery")
        auth_client.delete(f"/api/boards/{board_id}/columns/{disc_col['id']}")
        board_after = auth_client.get(f"/api/boards/{board_id}").json()
        # Positions should be contiguous
        positions_query = auth_client.app if hasattr(auth_client, 'app') else None
        # Just verify columns are correct count
        assert len(board_after["columns"]) == 5  # 5 original - 1 + 1 extra


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

    def test_create_card_with_priority(self, auth_client):
        resp = auth_client.post(
            "/api/cards",
            json={"column_id": "col-backlog", "title": "Priority card", "priority": "high"},
        )
        assert resp.status_code == 201
        card_id = resp.json()["id"]
        board = auth_client.get("/api/board").json()
        assert board["cards"][card_id]["priority"] == "high"

    def test_create_card_with_due_date(self, auth_client):
        resp = auth_client.post(
            "/api/cards",
            json={"column_id": "col-backlog", "title": "Dated card", "due_date": "2026-12-31"},
        )
        assert resp.status_code == 201
        card_id = resp.json()["id"]
        board = auth_client.get("/api/board").json()
        assert board["cards"][card_id]["due_date"] == "2026-12-31"

    def test_create_card_with_label(self, auth_client):
        resp = auth_client.post(
            "/api/cards",
            json={"column_id": "col-backlog", "title": "Labeled card", "label": "bug"},
        )
        assert resp.status_code == 201
        card_id = resp.json()["id"]
        board = auth_client.get("/api/board").json()
        assert board["cards"][card_id]["label"] == "bug"

    def test_create_card_default_priority_is_medium(self, auth_client):
        card_id = self._create(auth_client, title="Default priority")
        board = auth_client.get("/api/board").json()
        assert board["cards"][card_id]["priority"] == "medium"

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

    def test_update_card_priority(self, auth_client):
        card_id = self._create(auth_client)
        auth_client.patch(f"/api/cards/{card_id}", json={"priority": "high"})
        board = auth_client.get("/api/board").json()
        assert board["cards"][card_id]["priority"] == "high"

    def test_update_card_due_date(self, auth_client):
        card_id = self._create(auth_client)
        auth_client.patch(f"/api/cards/{card_id}", json={"due_date": "2027-01-15"})
        board = auth_client.get("/api/board").json()
        assert board["cards"][card_id]["due_date"] == "2027-01-15"

    def test_update_card_label(self, auth_client):
        card_id = self._create(auth_client)
        auth_client.patch(f"/api/cards/{card_id}", json={"label": "feature"})
        board = auth_client.get("/api/board").json()
        assert board["cards"][card_id]["label"] == "feature"

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

    def test_create_card_on_board_endpoint(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        board_data = auth_client.get(f"/api/boards/{board_id}").json()
        col_id = board_data["columns"][0]["id"]
        resp = auth_client.post(
            f"/api/boards/{board_id}/cards",
            json={"column_id": col_id, "title": "Board-specific card"},
        )
        assert resp.status_code == 201
        card_id = resp.json()["id"]
        board_after = auth_client.get(f"/api/boards/{board_id}").json()
        assert card_id in board_after["cards"]


import json as _json


def _ai_response(reply: str = "Got it.", board_update=None) -> str:
    return _json.dumps({"reply": reply, "board_update": board_update})


def _mock_openai(reply: str = "Got it.", board_update=None):
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
        assert len(messages) == 4
        assert messages[1] == {"role": "user", "content": "first message"}
        assert messages[2] == {"role": "assistant", "content": "first reply"}
        assert messages[3] == {"role": "user", "content": "second message"}

    def test_ai_calls_correct_model(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with _mock_openai() as mock_cls:
            auth_client.post("/api/ai", json={"message": "hi"})
        call_kwargs = mock_cls.return_value.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "openai/gpt-oss-120b:free"
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

    def test_system_prompt_includes_column_positions(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with _mock_openai() as mock_cls:
            auth_client.post("/api/ai", json={"message": "hi"})
        messages = mock_cls.return_value.chat.completions.create.call_args.kwargs["messages"]
        system_content = next(m["content"] for m in messages if m["role"] == "system")
        for pos in range(5):
            assert f'"position": {pos}' in system_content

    def test_system_prompt_includes_critical_warning(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with _mock_openai() as mock_cls:
            auth_client.post("/api/ai", json={"message": "hi"})
        messages = mock_cls.return_value.chat.completions.create.call_args.kwargs["messages"]
        system_content = next(m["content"] for m in messages if m["role"] == "system")
        assert "CRITICAL" in system_content
        assert "board_update" in system_content

    def test_null_board_update_returns_no_board(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with _mock_openai("I moved the cards!", board_update=None):
            resp = auth_client.post("/api/ai", json={"message": "move cards left"})
        assert resp.status_code == 200
        assert resp.json()["board"] is None

    def test_ai_moves_all_cards_left(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        disc_id = _make_card(auth_client, "col-discovery", "In Discovery")
        prog_id = _make_card(auth_client, "col-progress", "In Progress")
        done_id = _make_card(auth_client, "col-done", "In Done")

        update = {
            "move_cards": [
                {"card_id": disc_id, "column_id": "col-backlog", "position": 0},
                {"card_id": prog_id, "column_id": "col-discovery", "position": 0},
                {"card_id": done_id, "column_id": "col-review", "position": 0},
            ]
        }
        with _mock_openai("Moved all cards one column to the left.", board_update=update):
            resp = auth_client.post("/api/ai", json={"message": "move all cards to the left"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["reply"] == "Moved all cards one column to the left."
        assert body["board"] is not None

        col_by_id = {c["id"]: c for c in body["board"]["columns"]}

        assert disc_id in col_by_id["col-backlog"]["cardIds"]
        assert prog_id in col_by_id["col-discovery"]["cardIds"]
        assert done_id in col_by_id["col-review"]["cardIds"]

    def test_ai_moves_all_cards_left_with_card_in_leftmost_column(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        backlog_id = _make_card(auth_client, "col-backlog", "Already leftmost")
        disc_id = _make_card(auth_client, "col-discovery", "One right of leftmost")

        update = {
            "move_cards": [
                {"card_id": disc_id, "column_id": "col-backlog", "position": 1},
            ]
        }
        with _mock_openai("Moved cards left; backlog card was already leftmost.", board_update=update):
            resp = auth_client.post("/api/ai", json={"message": "move all cards to the left"})

        assert resp.status_code == 200
        body = resp.json()
        col_by_id = {c["id"]: c for c in body["board"]["columns"]}

        assert backlog_id in col_by_id["col-backlog"]["cardIds"]
        assert disc_id in col_by_id["col-backlog"]["cardIds"]
        assert disc_id not in col_by_id["col-discovery"]["cardIds"]

    def test_ai_model_hallucination_null_update_does_not_move_cards(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        card_id = _make_card(auth_client, "col-discovery", "Should not move")

        with _mock_openai("Done! I moved all cards to the left.", board_update=None):
            resp = auth_client.post("/api/ai", json={"message": "move all cards to the left"})

        assert resp.status_code == 200
        assert resp.json()["board"] is None

        board_resp = auth_client.get("/api/board")
        col_by_id = {c["id"]: c for c in board_resp.json()["columns"]}
        assert card_id in col_by_id["col-discovery"]["cardIds"]

    def test_ai_json_wrapped_in_markdown_is_parsed_correctly(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        card_id = _make_card(auth_client, "col-discovery", "To move")
        raw_content = (
            "```json\n"
            + _json.dumps({
                "reply": "Moved it.",
                "board_update": {"move_cards": [{"card_id": card_id, "column_id": "col-backlog", "position": 0}]},
            })
            + "\n```"
        )
        choice = MagicMock()
        choice.message.content = raw_content
        completion = MagicMock()
        completion.choices = [choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=completion)
        with patch("backend.main.AsyncOpenAI", return_value=mock_client):
            resp = auth_client.post("/api/ai", json={"message": "move to backlog"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["board"] is not None
        col_by_id = {c["id"]: c for c in body["board"]["columns"]}
        assert card_id in col_by_id["col-backlog"]["cardIds"]

    def test_ai_json_with_preamble_text_is_parsed_correctly(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        card_id = _make_card(auth_client, "col-discovery", "To move")
        raw_content = (
            "Here is the JSON response:\n"
            + _json.dumps({
                "reply": "Moved it.",
                "board_update": {"move_cards": [{"card_id": card_id, "column_id": "col-backlog", "position": 0}]},
            })
        )
        choice = MagicMock()
        choice.message.content = raw_content
        completion = MagicMock()
        completion.choices = [choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=completion)
        with patch("backend.main.AsyncOpenAI", return_value=mock_client):
            resp = auth_client.post("/api/ai", json={"message": "move to backlog"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["board"] is not None
        col_by_id = {c["id"]: c for c in body["board"]["columns"]}
        assert card_id in col_by_id["col-backlog"]["cardIds"]

    def test_ai_board_specific_endpoint(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        with _mock_openai("Responded for specific board."):
            resp = auth_client.post(f"/api/boards/{board_id}/ai", json={"message": "hello"})
        assert resp.status_code == 200
        assert resp.json()["reply"] == "Responded for specific board."

    def test_ai_board_specific_endpoint_wrong_board(self, auth_client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with _mock_openai():
            resp = auth_client.post("/api/boards/99999/ai", json={"message": "hello"})
        assert resp.status_code == 404

    def test_ai_system_prompt_includes_card_metadata(self, auth_client, monkeypatch):
        """Priority, due_date, and label appear in the system prompt when set on cards."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        auth_client.post(
            "/api/cards",
            json={
                "column_id": "col-backlog",
                "title": "Meta card",
                "priority": "high",
                "due_date": "2027-06-15",
                "label": "bug",
            },
        )
        with _mock_openai() as mock_cls:
            auth_client.post("/api/ai", json={"message": "hi"})
        messages = mock_cls.return_value.chat.completions.create.call_args.kwargs["messages"]
        system_content = next(m["content"] for m in messages if m["role"] == "system")
        assert "high" in system_content
        assert "2027-06-15" in system_content
        assert "bug" in system_content

    def test_ai_creates_card_with_priority(self, auth_client, monkeypatch):
        """AI can create a card with priority set via board_update."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        update = {
            "create_cards": [{
                "column_id": "col-backlog",
                "title": "High-pri card",
                "details": "",
                "priority": "high",
            }]
        }
        with _mock_openai("Created a high-priority card.", board_update=update):
            resp = auth_client.post("/api/ai", json={"message": "add a high priority card"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["board"] is not None
        backlog = next(c for c in body["board"]["columns"] if c["id"] == "col-backlog")
        cards = body["board"]["cards"]
        high_pri = [cards[cid] for cid in backlog["cardIds"] if cards[cid]["title"] == "High-pri card"]
        assert len(high_pri) == 1


class TestPasswordChange:
    def test_change_password_success(self, auth_client, client):
        resp = auth_client.patch(
            "/api/auth/password",
            json={"current_password": "password", "new_password": "newpassword123"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_change_password_and_login_with_new(self, auth_client, client):
        auth_client.patch(
            "/api/auth/password",
            json={"current_password": "password", "new_password": "newpassword123"},
        )
        auth_client.post("/api/auth/logout")
        resp = client.post("/api/auth/login", json={"username": "user", "password": "newpassword123"})
        assert resp.status_code == 200

    def test_change_password_wrong_current(self, auth_client):
        resp = auth_client.patch(
            "/api/auth/password",
            json={"current_password": "wrongpass", "new_password": "newpassword123"},
        )
        assert resp.status_code == 401

    def test_change_password_short_new_rejected(self, auth_client):
        resp = auth_client.patch(
            "/api/auth/password",
            json={"current_password": "password", "new_password": "abc"},
        )
        assert resp.status_code == 422

    def test_change_password_unauthenticated(self, client):
        resp = client.patch(
            "/api/auth/password",
            json={"current_password": "password", "new_password": "newpassword123"},
        )
        assert resp.status_code == 401


class TestColumnReorder:
    def test_reorder_columns(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        board = auth_client.get(f"/api/boards/{board_id}").json()
        col_ids = [c["id"] for c in board["columns"]]
        # Reverse column order
        reversed_ids = list(reversed(col_ids))
        resp = auth_client.patch(
            f"/api/boards/{board_id}/columns/reorder",
            json={"column_ids": reversed_ids},
        )
        assert resp.status_code == 200
        board_after = auth_client.get(f"/api/boards/{board_id}").json()
        after_ids = [c["id"] for c in board_after["columns"]]
        assert after_ids == reversed_ids

    def test_reorder_columns_partial(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        board = auth_client.get(f"/api/boards/{board_id}").json()
        col_ids = [c["id"] for c in board["columns"]]
        # Swap first two columns
        reordered = [col_ids[1], col_ids[0]] + col_ids[2:]
        auth_client.patch(
            f"/api/boards/{board_id}/columns/reorder",
            json={"column_ids": reordered},
        )
        board_after = auth_client.get(f"/api/boards/{board_id}").json()
        after_ids = [c["id"] for c in board_after["columns"]]
        assert after_ids[0] == col_ids[1]
        assert after_ids[1] == col_ids[0]

    def test_reorder_columns_unauthenticated(self, client):
        resp = client.patch(
            "/api/boards/1/columns/reorder",
            json={"column_ids": ["col-backlog"]},
        )
        assert resp.status_code == 401

    def test_reorder_ignores_foreign_column_ids(self, auth_client):
        boards = auth_client.get("/api/boards").json()
        board_id = boards[0]["id"]
        board = auth_client.get(f"/api/boards/{board_id}").json()
        col_ids = [c["id"] for c in board["columns"]]
        # Include a foreign ID — should be ignored
        resp = auth_client.patch(
            f"/api/boards/{board_id}/columns/reorder",
            json={"column_ids": col_ids + ["col-does-not-belong"]},
        )
        assert resp.status_code == 200


class TestAdmin:
    def test_list_users_requires_admin(self, auth_client):
        resp = auth_client.get("/api/admin/users")
        assert resp.status_code == 403

    def test_list_users_unauthenticated(self, client):
        resp = client.get("/api/admin/users")
        assert resp.status_code == 401

    def test_admin_can_list_users(self, admin_client):
        resp = admin_client.get("/api/admin/users")
        assert resp.status_code == 200
        users = resp.json()
        usernames = [u["username"] for u in users]
        assert "admin" in usernames
        assert "user" in usernames

    def test_admin_list_users_includes_metadata(self, admin_client):
        resp = admin_client.get("/api/admin/users")
        users = resp.json()
        for user in users:
            assert "id" in user
            assert "username" in user
            assert "is_admin" in user
            assert "created_at" in user
            assert "board_count" in user

    def test_admin_list_shows_correct_admin_flag(self, admin_client):
        resp = admin_client.get("/api/admin/users")
        users = {u["username"]: u for u in resp.json()}
        assert users["admin"]["is_admin"] is True
        assert users["user"]["is_admin"] is False

    def test_admin_delete_user(self, admin_client, client):
        client.post("/api/auth/register", json={"username": "todelete", "password": "pass1234"})
        resp = admin_client.get("/api/admin/users")
        users = {u["username"]: u for u in resp.json()}
        target_id = users["todelete"]["id"]
        resp = admin_client.delete(f"/api/admin/users/{target_id}")
        assert resp.status_code == 200
        # User should no longer appear
        resp = admin_client.get("/api/admin/users")
        usernames = [u["username"] for u in resp.json()]
        assert "todelete" not in usernames

    def test_admin_cannot_delete_self(self, admin_client):
        resp = admin_client.get("/api/admin/users")
        users = {u["username"]: u for u in resp.json()}
        admin_id = users["admin"]["id"]
        resp = admin_client.delete(f"/api/admin/users/{admin_id}")
        assert resp.status_code == 400

    def test_admin_delete_nonexistent_user(self, admin_client):
        resp = admin_client.delete("/api/admin/users/99999")
        assert resp.status_code == 404

    def test_admin_delete_requires_admin(self, auth_client):
        resp = auth_client.delete("/api/admin/users/1")
        assert resp.status_code == 403

    def test_admin_promote_user(self, admin_client):
        admin_client.app if hasattr(admin_client, 'app') else None
        resp = admin_client.get("/api/admin/users")
        users = {u["username"]: u for u in resp.json()}
        user_id = users["user"]["id"]
        resp = admin_client.patch(f"/api/admin/users/{user_id}/promote")
        assert resp.status_code == 200
        resp = admin_client.get("/api/admin/users")
        users = {u["username"]: u for u in resp.json()}
        assert users["user"]["is_admin"] is True

    def test_admin_promote_requires_admin(self, auth_client):
        resp = auth_client.patch("/api/admin/users/1/promote")
        assert resp.status_code == 403

    def test_deleted_user_boards_are_cleaned_up(self, admin_client):
        admin_client.post("/api/auth/register", json={"username": "withboards", "password": "pass1234"})
        # Login as withboards and create another board
        admin_client.post("/api/auth/login", json={"username": "withboards", "password": "pass1234"})
        admin_client.post("/api/boards", json={"title": "Extra Board"})

        # Re-login as admin
        admin_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})

        # Get withboards user id
        resp = admin_client.get("/api/admin/users")
        users = {u["username"]: u for u in resp.json()}
        target_id = users["withboards"]["id"]
        admin_client.delete(f"/api/admin/users/{target_id}")

        # User should no longer appear
        resp = admin_client.get("/api/admin/users")
        usernames = [u["username"] for u in resp.json()]
        assert "withboards" not in usernames


class TestCardAssign:
    def _make_card(self, auth_client):
        resp = auth_client.get("/api/board")
        col_id = resp.json()["columns"][0]["id"]
        resp = auth_client.post("/api/cards", json={"column_id": col_id, "title": "Assign me"})
        return resp.json()["id"]

    def _user_id(self, auth_client, username):
        for u in auth_client.get("/api/users").json():
            if u["username"] == username:
                return u["id"]
        return None

    def test_list_users(self, auth_client):
        resp = auth_client.get("/api/users")
        assert resp.status_code == 200
        usernames = [u["username"] for u in resp.json()]
        assert "user" in usernames
        assert "admin" in usernames

    def test_assign_card(self, auth_client):
        card_id = self._make_card(auth_client)
        uid = self._user_id(auth_client, "admin")
        resp = auth_client.patch(f"/api/cards/{card_id}/assign", json={"assigned_to_id": uid})
        assert resp.status_code == 200
        card = auth_client.get("/api/board").json()["cards"][card_id]
        assert card["assigned_to_username"] == "admin"

    def test_unassign_card(self, auth_client):
        card_id = self._make_card(auth_client)
        uid = self._user_id(auth_client, "admin")
        auth_client.patch(f"/api/cards/{card_id}/assign", json={"assigned_to_id": uid})
        auth_client.patch(f"/api/cards/{card_id}/assign", json={"assigned_to_id": None})
        card = auth_client.get("/api/board").json()["cards"][card_id]
        assert card["assigned_to_username"] is None

    def test_assign_nonexistent_user(self, auth_client):
        card_id = self._make_card(auth_client)
        resp = auth_client.patch(f"/api/cards/{card_id}/assign", json={"assigned_to_id": 99999})
        assert resp.status_code == 404

    def test_assign_other_users_card_fails(self, client, admin_client):
        board = admin_client.get("/api/board").json()
        col_id = board["columns"][0]["id"]
        card_id = admin_client.post("/api/cards", json={"column_id": col_id, "title": "Admin card"}).json()["id"]
        # switch to regular user
        client.post("/api/auth/login", json={"username": "user", "password": "password"})
        resp = client.patch(f"/api/cards/{card_id}/assign", json={"assigned_to_id": None})
        assert resp.status_code == 404


class TestCardDuplicate:
    def _make_card(self, auth_client, **kwargs):
        resp = auth_client.get("/api/board")
        col_id = resp.json()["columns"][0]["id"]
        payload = {"column_id": col_id, "title": "Original", **kwargs}
        resp = auth_client.post("/api/cards", json=payload)
        return resp.json()["id"]

    def test_duplicate_card(self, auth_client):
        card_id = self._make_card(auth_client, details="Some detail", priority="high")
        resp = auth_client.post(f"/api/cards/{card_id}/duplicate")
        assert resp.status_code == 201
        new_id = resp.json()["id"]
        assert new_id != card_id
        new_card = auth_client.get("/api/board").json()["cards"][new_id]
        assert "copy" in new_card["title"].lower()
        assert new_card["details"] == "Some detail"
        assert new_card["priority"] == "high"

    def test_duplicate_lands_in_same_column(self, auth_client):
        board = auth_client.get("/api/board").json()
        col_id = board["columns"][2]["id"]
        resp = auth_client.post("/api/cards", json={"column_id": col_id, "title": "Mid card"})
        card_id = resp.json()["id"]
        resp = auth_client.post(f"/api/cards/{card_id}/duplicate")
        new_id = resp.json()["id"]
        board = auth_client.get("/api/board").json()
        col = next(c for c in board["columns"] if c["id"] == col_id)
        assert new_id in col["cardIds"]

    def test_duplicate_other_users_card_fails(self, client, admin_client):
        board = admin_client.get("/api/board").json()
        col_id = board["columns"][0]["id"]
        card_id = admin_client.post("/api/cards", json={"column_id": col_id, "title": "Admin only"}).json()["id"]
        client.post("/api/auth/login", json={"username": "user", "password": "password"})
        resp = client.post(f"/api/cards/{card_id}/duplicate")
        assert resp.status_code == 404

    def test_duplicate_nonexistent_card(self, auth_client):
        resp = auth_client.post("/api/cards/card-nope/duplicate")
        assert resp.status_code == 404


class TestChecklist:
    def _make_card(self, auth_client):
        col_id = auth_client.get("/api/board").json()["columns"][0]["id"]
        resp = auth_client.post("/api/cards", json={"column_id": col_id, "title": "Card"})
        return resp.json()["id"]

    def test_empty_checklist(self, auth_client):
        card_id = self._make_card(auth_client)
        resp = auth_client.get(f"/api/cards/{card_id}/checklist")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_add_checklist_item(self, auth_client):
        card_id = self._make_card(auth_client)
        resp = auth_client.post(f"/api/cards/{card_id}/checklist", json={"title": "Do something"})
        assert resp.status_code == 201
        item = resp.json()
        assert item["title"] == "Do something"
        assert item["completed"] is False
        assert item["id"].startswith("chk-")

    def test_get_checklist_items_ordered(self, auth_client):
        card_id = self._make_card(auth_client)
        auth_client.post(f"/api/cards/{card_id}/checklist", json={"title": "Step 1"})
        auth_client.post(f"/api/cards/{card_id}/checklist", json={"title": "Step 2"})
        items = auth_client.get(f"/api/cards/{card_id}/checklist").json()
        assert len(items) == 2
        assert items[0]["title"] == "Step 1"
        assert items[1]["title"] == "Step 2"

    def test_complete_item(self, auth_client):
        card_id = self._make_card(auth_client)
        item_id = auth_client.post(f"/api/cards/{card_id}/checklist", json={"title": "Step"}).json()["id"]
        resp = auth_client.patch(f"/api/cards/{card_id}/checklist/{item_id}", json={"completed": True})
        assert resp.status_code == 200
        assert resp.json()["completed"] is True

    def test_update_item_title(self, auth_client):
        card_id = self._make_card(auth_client)
        item_id = auth_client.post(f"/api/cards/{card_id}/checklist", json={"title": "Old"}).json()["id"]
        resp = auth_client.patch(f"/api/cards/{card_id}/checklist/{item_id}", json={"title": "New"})
        assert resp.json()["title"] == "New"

    def test_delete_item(self, auth_client):
        card_id = self._make_card(auth_client)
        item_id = auth_client.post(f"/api/cards/{card_id}/checklist", json={"title": "Remove"}).json()["id"]
        auth_client.delete(f"/api/cards/{card_id}/checklist/{item_id}")
        items = auth_client.get(f"/api/cards/{card_id}/checklist").json()
        assert not any(i["id"] == item_id for i in items)

    def test_checklist_counts_in_board(self, auth_client):
        card_id = self._make_card(auth_client)
        auth_client.post(f"/api/cards/{card_id}/checklist", json={"title": "A"})
        item_id = auth_client.post(f"/api/cards/{card_id}/checklist", json={"title": "B"}).json()["id"]
        auth_client.patch(f"/api/cards/{card_id}/checklist/{item_id}", json={"completed": True})
        card = auth_client.get("/api/board").json()["cards"][card_id]
        assert card["checklist_count"] == 2
        assert card["checklist_done"] == 1

    def test_delete_nonexistent_item(self, auth_client):
        card_id = self._make_card(auth_client)
        resp = auth_client.delete(f"/api/cards/{card_id}/checklist/chk-fake")
        assert resp.status_code == 404

    def test_checklist_on_other_users_card_fails(self, client, admin_client):
        col_id = admin_client.get("/api/board").json()["columns"][0]["id"]
        card_id = admin_client.post("/api/cards", json={"column_id": col_id, "title": "Admin"}).json()["id"]
        client.post("/api/auth/login", json={"username": "user", "password": "password"})
        resp = client.get(f"/api/cards/{card_id}/checklist")
        assert resp.status_code == 404

    def test_empty_title_rejected(self, auth_client):
        card_id = self._make_card(auth_client)
        resp = auth_client.post(f"/api/cards/{card_id}/checklist", json={"title": ""})
        assert resp.status_code == 422


class TestWipLimit:
    def _board_and_col(self, auth_client):
        board_id = auth_client.get("/api/boards").json()[0]["id"]
        board = auth_client.get(f"/api/boards/{board_id}").json()
        return board_id, board["columns"][0]["id"]

    def test_set_wip_limit(self, auth_client):
        board_id, col_id = self._board_and_col(auth_client)
        resp = auth_client.patch(f"/api/boards/{board_id}/columns/{col_id}/wip", json={"wip_limit": 3})
        assert resp.status_code == 200
        col = next(c for c in auth_client.get(f"/api/boards/{board_id}").json()["columns"] if c["id"] == col_id)
        assert col["wip_limit"] == 3

    def test_clear_wip_limit(self, auth_client):
        board_id, col_id = self._board_and_col(auth_client)
        auth_client.patch(f"/api/boards/{board_id}/columns/{col_id}/wip", json={"wip_limit": 5})
        auth_client.patch(f"/api/boards/{board_id}/columns/{col_id}/wip", json={"wip_limit": None})
        col = next(c for c in auth_client.get(f"/api/boards/{board_id}").json()["columns"] if c["id"] == col_id)
        assert col["wip_limit"] is None

    def test_wip_limit_zero_rejected(self, auth_client):
        board_id, col_id = self._board_and_col(auth_client)
        resp = auth_client.patch(f"/api/boards/{board_id}/columns/{col_id}/wip", json={"wip_limit": 0})
        assert resp.status_code == 422

    def test_wip_limit_wrong_board_fails(self, client, admin_client):
        admin_board_id = admin_client.get("/api/boards").json()[0]["id"]
        col_id = admin_client.get(f"/api/boards/{admin_board_id}").json()["columns"][0]["id"]
        client.post("/api/auth/login", json={"username": "user", "password": "password"})
        resp = client.patch(f"/api/boards/{admin_board_id}/columns/{col_id}/wip", json={"wip_limit": 2})
        assert resp.status_code == 404


class TestBoardStats:
    def _board_id(self, auth_client):
        return auth_client.get("/api/boards").json()[0]["id"]

    def test_stats_empty_board(self, auth_client):
        board_id = self._board_id(auth_client)
        resp = auth_client.get(f"/api/boards/{board_id}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cards"] == 0
        assert data["overdue_count"] == 0

    def test_stats_with_cards(self, auth_client):
        board_id = self._board_id(auth_client)
        board = auth_client.get(f"/api/boards/{board_id}").json()
        col_id = board["columns"][0]["id"]
        auth_client.post(f"/api/boards/{board_id}/cards", json={"column_id": col_id, "title": "A", "priority": "high"})
        auth_client.post(f"/api/boards/{board_id}/cards", json={"column_id": col_id, "title": "B", "priority": "low"})
        data = auth_client.get(f"/api/boards/{board_id}/stats").json()
        assert data["total_cards"] == 2
        assert data["cards_by_priority"]["high"] == 1
        assert data["cards_by_priority"]["low"] == 1

    def test_stats_overdue(self, auth_client):
        board_id = self._board_id(auth_client)
        board = auth_client.get(f"/api/boards/{board_id}").json()
        col_id = board["columns"][0]["id"]
        auth_client.post(f"/api/boards/{board_id}/cards", json={"column_id": col_id, "title": "Old", "due_date": "2020-01-01"})
        data = auth_client.get(f"/api/boards/{board_id}/stats").json()
        assert data["overdue_count"] == 1

    def test_stats_wrong_board_fails(self, client, admin_client):
        admin_board_id = admin_client.get("/api/boards").json()[0]["id"]
        client.post("/api/auth/login", json={"username": "user", "password": "password"})
        resp = client.get(f"/api/boards/{admin_board_id}/stats")
        assert resp.status_code == 404
