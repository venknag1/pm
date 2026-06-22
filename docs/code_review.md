# Code Review: Project Management MVP

## Overview

This is a well-structured MVP with a Next.js frontend, FastAPI backend, SQLite database, and OpenRouter AI integration. The codebase demonstrates solid engineering practices. Below are findings organized by severity.

---

## CRITICAL

### 1. API Key Exposed in Repository
- **File:** `.env:1` contains a live `OPENROUTER_API_KEY`
- The `.gitignore` excludes `.env`, but if this file was ever committed to git history, the key is compromised.
- **Fix:** Rotate the key immediately. Check `git log` for any committed `.env` files.

### 2. Hardcoded Secret Key Fallback
- **File:** `backend/auth.py:7-9`
- `URLSafeSerializer` falls back to `"dev-secret-key-change-in-production"` if `SECRET_KEY` env var is not set. In Docker production, if `.env` doesn't mount correctly, sessions are signed with a public default key -- anyone can forge session tokens.
- **Fix:** Raise an error at startup if `SECRET_KEY` is not set, or use a randomly generated value per container instance.

---

## HIGH

### 3. Session Cookie Missing `secure` and `SameSite` Hardening
- **File:** `backend/main.py:256-261`
- The session cookie is set with `httponly=True, samesite="lax"` but no `secure=True`. In production over HTTPS, cookies should also be `secure`.
- **Fix:** Add `secure=True` in production (or conditionally based on env).

### 4. SQLite `check_same_thread=False` in Async Context
- **File:** `backend/db.py:19`
- SQLite connections are created with `check_same_thread=False`, which disables a safety check. While FastAPI uses a thread pool for sync route handlers, this could mask concurrency bugs if the code evolves.
- **Mitigation:** Acceptable for MVP with single-writer SQLite, but document the limitation.

### 5. No CSRF Protection on State-Changing Endpoints
- **Files:** `backend/main.py` -- PATCH/POST/DELETE endpoints
- The session cookie is `SameSite=Lax`, which provides partial CSRF protection for POST. However, PATCH and DELETE are vulnerable to CSRF from same-site requests in older browsers.
- **Mitigation:** Acceptable for MVP; consider CSRF tokens for production.

### 6. Board State Not Refreshed After AI Mutations
- **File:** `backend/main.py:444-488`
- The `ai_chat` endpoint applies board updates and returns the new board, but there's no locking or optimistic concurrency. If two AI requests run simultaneously, one could overwrite the other's changes.
- **Mitigation:** Acceptable for single-user MVP.

---

## MEDIUM

### 7. Duplicate `API_BASE` Definitions
- **Files:** `frontend/src/lib/api.ts:8` and `frontend/src/lib/auth.ts:1`
- Both files independently define `const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? ""`. This should be a shared constant.
- **Fix:** Extract to `frontend/src/lib/config.ts`.

### 8. Frontend Optimistic UI Without Error Recovery
- **Files:** `frontend/src/components/KanbanBoard.tsx:49-104`
- `handleDragEnd`, `handleRenameColumn`, `handleDeleteCard` update local state immediately and fire API calls. If the API call fails (`.catch(console.error)`), the UI is out of sync with the server.
- **Fix:** On API failure, roll back local state or re-fetch the board.

### 9. No Loading State on Initial Board Fetch
- **File:** `frontend/src/components/KanbanBoard.tsx:39-41`
- `getBoard().then(setBoard).catch(console.error)` -- on error, `board` stays `null` and the user sees "Loading board..." indefinitely with no retry option.
- **Fix:** Add error state and a retry button.

### 10. No Input Validation on Column Rename
- **File:** `frontend/src/components/KanbanColumn.tsx:42-47`
- The column title input has no `maxLength`, no debouncing, and fires `onRename` on every keystroke. This sends a PATCH request per character typed.
- **Fix:** Debounce the API call (the local state update is fine on each keystroke for responsiveness).

### 11. Missing Error Boundaries
- **Files:** All React components
- No React error boundaries exist. If a component throws during render (e.g., from malformed board data after AI update), the entire app crashes with a white screen.
- **Fix:** Add an error boundary around `KanbanBoard` and `AISidebar`.

### 12. Test Fixtures in `test_ai_live.py` Duplicate `conftest.py`
- **File:** `backend/tests/test_ai_live.py:10-21`
- The `client` and `auth_client` fixtures are duplicated. pytest fixtures in `conftest.py` should be shared.
- **Fix:** Remove the duplicated fixtures from `test_ai_live.py` and rely on `conftest.py`.

---

## LOW

### 13. `_new_id` Timestamp Prefix Not Monotonic
- **File:** `backend/main.py:73-76`
- Uses `hex(int(time.time() * 1000))` which could collide if called multiple times in the same millisecond within the same process. The 6-char random suffix mitigates this, but a UUID would be cleaner.
- **Severity:** Low -- collision probability is negligible for an MVP.

### 14. `_apply_board_update` Does Not Validate Position Bounds
- **File:** `backend/main.py:138-239`
- The `move_cards` handler doesn't validate that `position` is within the valid range for the target column. Out-of-bounds positions are accepted silently.
- **Fix:** Clamp or reject positions exceeding column length.

### 15. AI Prompt Uses f-string-style Formatting with User-Controlled JSON
- **File:** `backend/main.py:34-53`
- The system prompt embeds `board_json` via `.format()`. While the board JSON is server-generated (not user input), if future changes allow user-provided board content, this could cause prompt injection.
- **Mitigation:** Current implementation is safe, but worth noting for future changes.

### 16. `KanbanColumn` Input Has No Blur Handler
- **File:** `frontend/src/components/KanbanColumn.tsx:42-47`
- If the user clicks away from the column title input without pressing Tab, the rename is still sent (since `onChange` fires immediately). This is acceptable UX but differs from the e2e test which uses `page.keyboard.press("Tab")`.

### 17. Frontend `Card` Type Uses `details` While Backend Uses `details`
- Both are consistent (`details`), which is good. No mismatch found.

### 18. Dockerfile Does Not Copy `.env` File
- **File:** `Dockerfile:1-27`
- The Dockerfile doesn't copy the `.env` file. The `start.sh` uses `--env-file .env` at runtime, which is the correct pattern. No issue here.

### 19. Scripts Only Cover Unix
- **Files:** `scripts/start.sh`, `scripts/stop.sh`
- PowerShell scripts exist (`start.ps1`, `stop.ps1`) for Windows, which is good. No Linux-specific issues found.

---

## POSITIVE OBSERVATIONS

1. **Clean architecture**: Backend has clear separation (models, db, auth, main). Frontend has a well-organized component hierarchy.
2. **Good test coverage**: Backend tests cover auth, board CRUD, columns, cards, and AI integration with mocked OpenAI. Frontend has both unit tests (vitest) and e2e tests (playwright).
3. **Proper TypeScript types**: Frontend uses typed props, API responses, and board data models throughout.
4. **Well-designed AI integration**: Structured output with `BoardUpdate` model, graceful handling of malformed AI responses, and proper validation of AI-generated mutations.
5. **Consistent coding style**: Tailwind classes follow the color scheme from AGENTS.md. Backend follows FastAPI conventions.
6. **Database schema**: Uses proper foreign keys, text-based IDs with prefixes for readability, and position-based ordering.

---

## RECOMMENDATIONS FOR PRODUCTION

1. Rotate the exposed API key
2. Add `SECRET_KEY` as a required env var with no default
3. Add rate limiting to `/api/ai` endpoint
4. Implement error boundaries in React
5. Add debouncing to column rename API calls
6. Consider adding optimistic locking or a simple mutex for AI board updates
