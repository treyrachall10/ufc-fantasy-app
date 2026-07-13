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

docker compose exec web python manage.py enqueue_event_sync

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

Start the frontend development server:

```
npm start
```

---

# Development Workflow

## Backend + workers

```
docker compose up --build
```

## Frontend

```
npm start
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
