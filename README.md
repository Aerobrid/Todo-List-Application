# Full-Stack AI-Forward Task Manager (Intern Applied AI Assessment)

A high-performance, low-latency, and secure full-stack Todo List application designed with a **FastAPI** backend, **SQLite** transactional database, and a **Vanilla JS/CSS** developer-tool frontend. 

It implements all primary and bonus assignment features, along with applied AI capabilities and security measures.

---

## Technical Stack & Architectural Choices

### 1. Backend: FastAPI (Python)
* **High Performance**: FastAPI leverages `anyio` for asynchronous execution, making it one of the fastest Python web frameworks available.
* **Schema Validation**: Powered by `Pydantic`, ensuring strict type checking and data serialization boundaries between client payloads and the database.
* **Auto OpenAPI Docs**: Automatically generates interactive API documentation (available at `/docs`).

### 2. Database: SQLite + SQLAlchemy
* **Zero Configuration, Persistent**: SQLite stores data in a single local file (`tasks.db`), meaning the project runs out-of-the-box without installing database servers like PostgreSQL or MySQL.
* **Modularity**: By using **SQLAlchemy 2.0 ORM**, the database engine can be swapped (e.g. to PostgreSQL) by modifying a single connection string in `config.py` without rewriting queries.
* **Write-Ahead Logging (WAL)**: Configured in `database.py`. WAL allows concurrent readers to access the database without being blocked by active writes, minimizing execution latency.
* **Foreign Key Constraints**: Explicitly enabled on connection setup, ensuring database integrity and cascade deletions (relational subtasks are purged when a task is deleted).

### 3. Frontend: Semantic HTML5 + Vanilla JS/CSS
* **Neutral Developer UI**: Styled as a clean, responsive wireframe scaffold. It avoids translucent panels, glassmorphic blurs, glowing lights, or heavy gradients. It prioritizes layout consistency, readability, and solid borders.
* **Concern Isolation**: 
  - `index.html` holds semantic HTML structures (header, main, sections, tags) and ARIA parameters for screen readers.
  - `style.css` defines tokenized properties (colors, border-radii, spacing) and handles grid layouts.
  - `api.js` isolates async AJAX requests using `fetch`.
  - `app.js` runs event handling, client-side state caching, sorting, and DOM updates.

---

## Key Features

1. **Standard CRUD Operations**:
   - Add, edit, toggle, and delete tasks.
   - Edit inline: Clicking "Edit" populates the creation form, highlighting changes.
   - Bulk deletion of completed items via "Clear Completed".
2. **Relational Subtasks & Cascading Completion**:
   - Tasks support checklists.
   - Subtasks can be checked off or deleted independently, and are nested inside the parent task.
   - **Cascading Completion**: Checking off a parent task automatically runs a database transaction that marks all of its child subtasks as completed, improving productivity workflow speed.
3. **Filter, Search, & Dynamic Custom Categories**:
   - Filter by status (All, Active, Completed).
   - Search query updates in real-time with a built-in 300ms input de-bounce to protect database load.
   - Client-side sorting options: Newest First, Due Date (Soonest), and Priority (High to Low).
   - **Dynamic Custom Categories**: Instead of restricting users to static dropdown options, categories are persisted as flexible strings (`String(50)`). Selecting "+ Add Custom..." in the UI reveals a text input to save any category name.
4. **Flexible Calendar and Due Times**:
   - Implements a checkbox toggle for **Add Time** next to the date input.
   - Date-only selections default to UTC Noon (`12:00:00Z`) to prevent timezone offsets from slipping the display day.
   - Date + Time selections combine input fields and convert local times into UTC timezone-aware strings.
5. **Applied AI Integrations**:
   - **Subtask Suggestion Generator**: Clicking "Generate Subtasks" on a task analyzes its title/description and automatically appends a logical 3-5 item checklist breakdown using the Gemini API.
   - **Dynamic Feature Control**: If the `GEMINI_API_KEY` is not configured in the environment, the subtask generation buttons are dynamically hidden from the UI, keeping the interface clean and functional.

---

## Security Engineering

1. **Cross-Site Scripting (XSS) Prevention**: All inbound strings are processed through `html.escape` inside `app/security.py` prior to database commit, neutralizing `<script>` tags or malicious event attributes.
2. **Defensive Response Headers**:
   - `X-Frame-Options: DENY` (Clickjacking defense).
   - `X-Content-Type-Options: nosniff` (MIME sniffing defense).
   - `Content-Security-Policy (CSP)` restricts executable sources strictly to the local origin.
3. **Sliding-Window Rate Limiting**: Simple in-memory rate limiting stops brute force spamming:
   - Query routes (`GET`): Limit 100 requests per IP per minute.
   - Mutation routes (`POST`, `PUT`, `DELETE`): Limit 30 requests per IP per minute.
4. **Hidden Environment Loading**: Configured with `load_dotenv()` to pull API keys directly from a hidden `.env` file on startup. If a key is already exported in the shell (e.g., via PowerShell), it takes precedence and is not overwritten.

---

## Directory Structure

```
amplify-federal/
├── .github/
│   └── workflows/
│       └── test.yml       # GitHub Actions CI pipeline
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI setup, middleware, and mount endpoints
│   ├── config.py          # Pydantic BaseSettings environment parsing & dotenv load
│   ├── database.py        # SQLite SQLAlchemy configuration & WAL setup
│   ├── models.py          # SQLAlchemy models and Pydantic schemas
│   ├── crud.py            # SQLite CRUD query transactions (with cascade completion)
│   ├── security.py        # Input sanitization and Rate Limiter
│   ├── router/
│   │   ├── __init__.py
│   │   ├── tasks.py       # Task CRUD routes
│   │   └── ai.py          # Subtask generator endpoints
│   └── static/            # Frontend files served by FastAPI
│       ├── index.html
│       ├── css/
│       │   └── style.css  # Contains text-wrapping and layout rules
│       └── js/
│           ├── api.js     # Isolated network operations
│           └── app.js     # DOM state controller
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # Pytest database and TestClient fixtures
│   ├── test_crud.py       # Database CRUD unit tests (includes cascade completions)
│   └── test_api.py        # Endpoint and middleware integration tests (includes XSS & clearing)
├── .gitignore
├── Dockerfile             # Multi-stage image packaging with test gate
├── requirements.txt       # Pinned library dependencies
├── run.py                 # Virtual env builder and Uvicorn launcher
└── README.md              # Documentation
```

---

## Installation & Setup

### Option 1: Automatic Setup Script (Recommended)
You can set up and run the application with a single command. Ensure Python 3.11+ is installed.
Run:
```bash
python run.py
```
This script will:
1. Create a Python virtual environment (`.venv`).
2. Upgrade `pip` and install all pinned dependencies from `requirements.txt`.
3. Start the server locally at `http://127.0.0.1:8000`.

---

### Option 2: Manual Development Setup

1. **Create and Activate Virtual Environment**:
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure AI Features (Optional)**:
   Add your Gemini API key to a local `.env` file in the root directory:
   ```env
   GEMINI_API_KEY="your-gemini-key"
   ```
   Or set it in your terminal environment if preferred:
   ```bash
   # Windows (Powershell)
   $env:GEMINI_API_KEY="your-gemini-key"
   # Linux/macOS
   export GEMINI_API_KEY="your-gemini-key"
   ```
4. **Run Application**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

---

### Option 3: Run via Docker
The application is packaged with a multi-stage `Dockerfile`. The build compiles dependencies, copies source code, and runs the entire test suite as a compiler gate. If a test fails, the image will not build.

1. **Build Image**:
   ```bash
   docker build -t amplify-todo-app .
   ```
2. **Run Container**:
   ```bash
   docker run -d -p 8000:8000 amplify-todo-app
   ```
3. Open `http://localhost:8000` in your web browser.

---

## Running the Automated Test Suite

We use `pytest` for unit and integration testing. Database connections are redirected to an ephemeral, in-memory SQLite state during runs.

1. **Run tests**:
   ```bash
   pytest -v
   ```
2. This runs assertions verifying:
   - Database operations (Task/Subtask additions, timestamp checks, subtask cascade completions).
   - API endpoints (Status codes, payload structural requirements, description clearing updates).
   - Input sanitization logic (Script stripping checks).
   - Rate limiting filters (Checks that the 101st request returns HTTP 429).
3. **Other**:
   ```bash
   # 2. Run specific test files
   pytest tests/test_api.py -v
   pytest tests/test_crud.py -v

   # 3. Generate a coverage report (requires pytest-cov)
   pip install pytest-cov
   pytest --cov=app tests/ -v
   ```
---

## Technical Summary

### 1. Architectural Blueprint (Separation of Concerns)
* **Decoupled Frontend**: Built as a responsive SPA (Single Page Application) using semantic HTML5 and vanilla JavaScript/CSS. Frontend concerns are strictly isolated:
  - `api.js` encapsulates all `fetch` request protocols.
  - `app.js` manages local state, event routing, sorting algorithms, and DOM rendering.
  - `style.css` declares tokenized properties (colors, border-radii, spacing) and manages grid layouts without utility-class clutter.
* **ASGI Backend (FastAPI)**: Serves high-performance, asynchronous REST endpoints. Request schemas and response formats are strictly validated via Pydantic model definitions, providing clear documentation boundaries.

### 2. High-Performance Persistence (SQLite Tuning)
* **Write-Ahead Logging (WAL)**: Enabled on connection startup. Unlike traditional rollback journals, WAL allows multiple reader processes to run concurrently with a writer process, significantly increasing concurrency and throughput for concurrent users.
* **Foreign Key Constraints & Cascade purges**: SQLite disables foreign key enforcement by default. We programmatically enable it on SQLAlchemy engine setup (`PRAGMA foreign_keys = ON`), guaranteeing relational integrity. When a task is deleted, its subtasks are cleaned up atomically.
* **Timezone Consistency**: Saved as timezone-naive local datetimes, which allows due dates to act like calendar events: scheduling a task for `12:00 PM` displays as `12:00 PM` globally, avoiding shift changes caused by UTC timezone offsets on the client machine.

### 3. Production Security Hardening
* **XSS Ingestion Gate**: Every string parameter submitted to database mutations passes through `html.escape` (stripping or translating HTML tags like `<script>`), rendering persistent script injection attacks harmless.
* **Sliding-Window Rate Limiter**: Configured on the API router using standard Python queues. Blocks bot spamming by capping GET routes to 100 requests/min and POST/PUT/DELETE routes to 30 requests/min.
* **Defensive HTTP Headers**: The app injects secure middleware headers:
  - `X-Frame-Options: DENY` to stop Clickjacking attacks.
  - `X-Content-Type-Options: nosniff` to prevent MIME-type sniffing.
  - `Content-Security-Policy` restricts script and style sources to prevent malicious code executions.

### 4. Applied AI Integration
* **Subtask Suggestion Generator**: Leverages the official Google GenAI (`google-genai`) SDK using the fast `gemini-2.5-flash` model. It compiles task details and generates 3 to 5 logical subtask suggestions returned as a structured JSON list.
* **Dynamic Feature Visibility**: If no `GEMINI_API_KEY` is present, the frontend dynamically queries `/api/ai/config` on load to hide the AI components. This removes non-functional buttons from the interface entirely, keeping the application workspace clean.

### 5. Architectural Weak Points & Mitigation Plan
* **Stateful Rate Limiting**: The sliding-window rate limiter stores request timestamps in-memory. In a distributed, multi-node cloud environment, clients could bypass limits by hit-routing across different nodes. *Mitigation:* Relocate the rate-limiting state to a centralized Redis instance using standard token-bucket libraries.
* **Synchronous Database Operations**: The SQLite engine executes synchronous database calls. In high-traffic environments, thread pools might block while waiting for disk I/O operations. *Mitigation:* Migrate the database session layer to `aiosqlite` and utilize FastAPI's async/await capabilities with SQLAlchemy `AsyncSession`.
* **Single-User Scope**: All tasks are stored in a single table without user isolation barriers. *Mitigation:* Integrate an authentication layer using OAuth2 and JWT bearer tokens, indexing all task rows to a unique `user_id` foreign key.

### 6. Production Road Map (Future Improvements)
* **Real-Time Synchronizations**: Implement WebSockets or Server-Sent Events (SSE) to sync task and subtask modifications across multiple open browser tabs instantly.
* **IndexedDB Offline PWA Cache**: Cache tasks using browser-based Service Workers and an IndexedDB layer. Sync local offline changes automatically when a network connection is detected.
* **Advanced Coverage Tracking**: Integrate code coverage reporting to monitor test coverage percentage line-by-line.
