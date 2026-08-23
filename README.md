## Lessons Learned, Improvements & Future Features

UFC Fantasy is my first fully deployed application. I began building it before taking advanced software engineering courses or completing a software engineering internship, so several architectural decisions reflect what I knew at the time. The project has been valuable for learning where stronger architecture, testing, observability, and separation of concerns matter in a real system.

### Architectural Lessons Learned

* **Backend Application Structure** — Most backend functionality currently lives inside one large Django application. A better approach would have been a modular monolith organized around domains such as `fighters`, `events`, `users`, and `fantasy`.
* **Domain Boundaries** — Clear domain boundaries would improve separation of concerns and make individual components easier to extract into separate services if scaling requirements ever justified it.
* **Dependency Rules** — Circular imports and dependency direction were not considered early enough. A stronger architecture would explicitly define which modules can depend on and communicate with one another.
* **Dependency Injection** — External clients such as the Supabase client are imported directly in several places. Injecting these dependencies would improve testing, configuration, and replacement of external services.
* **Internal Architecture** — Each domain could use a consistent feature-based or clean-architecture structure with clear dependency rules rather than mixing business logic, persistence, and API concerns.
* **API Layer Separation** — The API could have been designed as a thin layer over domain/application logic. This would allow the application to expose one unified API while keeping internal domains independently maintainable and easier to separate later.
* **Views Contain Too Much Logic** — Django views should primarily handle HTTP concerns and orchestration. More implementation details could have been moved into application/service functions, following a flow closer to `URL → View → Service/Resolver → Serializer → Client/Repository`.
* **Database Design** — Some tables could have clearer schemas and additional metadata such as `created_at` timestamps for readability, debugging, and auditing.
* **Worker Consistency** — Data-pipeline workers evolved over time and do not all follow the same leasing, retry, and lifecycle conventions. A shared worker execution model would reduce complexity.
* **Service Boundaries** — Some workers currently call the application's API to update database state. This was intentionally introduced to practice service boundaries similar to a microservice architecture, but direct persistence or a better-defined messaging/application boundary would be more appropriate for this system.
* **Design for Modularity First** — The largest architectural lesson from the project is that a well-structured modular monolith would have provided most of the desired separation without introducing unnecessary distributed-system complexity.

### Areas to Improve

* **UI/UX Redesign** — The current interface is functional but visually limited and could benefit from a broader design overhaul.
* **Career Statistics Accuracy** — Some fighter career statistics are currently outdated because earlier database and business-logic changes affected historical data. These statistics are corrected automatically the next time the fighter competes. A full historical rebuild is possible but is intentionally deferred to avoid unnecessary cloud-processing costs.
* **Caching** — Frequently accessed data such as user information, teams, and league information could be cached more effectively.
* **Observability** — The application does not yet have a complete observability stack. Distributed tracing, metrics, and centralized monitoring through tools such as OpenTelemetry and Datadog would improve debugging and operational visibility.
* **Testing** — Test coverage and test isolation could be improved, particularly around external clients, workers, and integration boundaries.
* **Environment Separation** — The current cloud development environment also serves as the production environment due to cost constraints. A dedicated staging/load-testing environment would be preferable for a larger production system.
* **Code Consistency** — More consistent conventions around comments, function structure, naming, and general code organization should have been established earlier.

### Planned Features

* **Draft Lobby Animations** — Add animations and transitions to improve the live draft experience.
* **League Season Management** — Add a scheduled service/worker that detects when a league's season has ended and either notifies owners or cleans up expired leagues.
* **Team Notifications** — Notify team owners when one of their drafted fighters competes.
* **Weekly Fight Card Summary** — Generate a summary showing which fighters on a user's team competed during the week and their results.
* **Improved Mobile Support** — Improve responsive layouts and the overall mobile experience.

# UFC Fantasy App

Containerized **Django backend** with a **React frontend** for a UFC fantasy sports application.

The backend runs inside Docker and connects to a **Supabase PostgreSQL database**.  
The frontend runs locally during development.

---

# Prerequisites

Install the following before running the project:

- Docker Desktop
- Node.js (v18+)
- npm
- Visual Studio Code (recommended)

Optional:

- VS Code Docker Extension (Microsoft)

---

# Clone the Repository

```bash
git clone https://github.com/<your-username>/ufc-fantasy-app.git
cd ufc-fantasy-app
```

---

# Database Setup (Supabase)

This project uses **Supabase PostgreSQL** instead of a local Docker database.

## 1. Create a Supabase Project

Go to:

https://supabase.com

Create a new project.  
This project is intended for **personal development use**.

---

## 2. Get the Database Connection Info

In the Supabase dashboard:

Project Settings → Database → Connect

Change the connection method to:

Transaction Pooler

Copy the values provided under **View Parameters**.

---

## 3. Create the `.env` File

Copy the example env file in the **same directory as `docker-compose.yml`**:

```bash
cp .env.example .env
```

Fill in Supabase DB credentials, API keys, and other secrets. Do not commit `.env`.

Compose overrides `PUBSUB_EMULATOR_HOST` and API base URLs inside containers so services talk over the Docker network (`pubsub:8085`, `http://web:8000`). Keep host-oriented values in `.env` for IDE debugging.

---

# Running the Backend

Build and start the full local stack (API, Pub/Sub emulator, and pipeline workers):

```bash
docker compose up --build
```

This starts:

- `web` — Django API on `http://localhost:8000`
- `pubsub` / `pubsub-init` — local Pub/Sub emulator and topics
- `fighter-profile-worker`, `fights-in-event-worker`, `fight-stats-worker`, `career-stats-worker`
- image scraper / image worker jobs

Workers keep listening while idle in Compose (`WORKER_IDLE_SHUTDOWN_ENABLED=false`).

---

# Pipeline development workflow

1. Start the stack: `docker compose up --build`
2. Enqueue a test job from the Django container:

```bash
docker compose exec web python manage.py enqueue_fight_stats \
  --fight-id 1 \
  --fight-url 'http://ufcstats.com/fight-details/...'
```

```bash
docker compose exec web python manage.py enqueue_career_stats --fight-id 1
```

Other useful commands:

```bash
docker compose exec web python manage.py enqueue_fight_import \
  --event-id 1 \
  --url 'http://ufcstats.com/event-details/...'

docker compose exec web python manage.py enqueue_fighter_profile \
  --fighter-id 1 \
  --fighter-url 'http://ufcstats.com/fighter-details/...'

docker compose exec web python manage.py watch_events

docker compose exec web python manage.py init_pubsub_emulator
```

3. Watch the matching worker logs process the message.

Prefer `docker compose exec web …` so Pub/Sub and API URLs match the Compose network.

---

# Legacy bulk populate

For the older CSV-style scrape into the DB:

```bash
docker compose exec web python manage.py refresh_ufc_data
```

---

# Frontend Setup

Navigate to the frontend directory:

```
cd frontend/ufc-fantasy-frontend
```

Install dependencies:

```
npm install
```

Start the frontend against the **local** Django API (`http://localhost:8000`):

```
npm start
```

Or, equivalently:

```
npm run start:dev-local
```

Start the same frontend against the **cloud** main API (no source URL edits):

```
npm run start:dev-cloud
```

Produce a production bundle configured for the cloud API:

```
npm run build:dev-cloud
```

`npm run build` remains a plain Create React App build and does not load the cloud env file. Frontend CI uses `build:dev-cloud`. A later Vercel deploy should set the same `REACT_APP_*` values as `.env.dev-cloud` (or run `build:dev-cloud`); do not invent a frontend domain in source. When a hosted origin exists, add it to the Auth0 application's Allowed Callback URLs, Logout URLs, and Web Origins.

---

# Development Workflow

## Backend + workers

```
docker compose up --build
```

## Frontend

```
npm start                 # CRA dev server → local API (same as start:dev-local)
npm run start:dev-cloud   # CRA dev server → cloud API
npm run build:dev-cloud   # production bundle configured for the cloud API
```

---

# Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5 |
| Database | Supabase PostgreSQL |
| Frontend | React |
| Containerization | Docker + Docker Compose |
| Package Manager | npm |

---

# Project Summary

To run the project:

1. Clone the repository
2. Create a Supabase project
3. Add database credentials to `.env`
4. Run the Docker container
5. Populate the database
6. Start the frontend

After these steps the entire application runs locally.
