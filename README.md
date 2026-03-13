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

Create a `.env` file in the **same directory as `docker-compose.yml`**.

Example project structure:

```
ufc-fantasy-app/
│
├── docker-compose.yml
├── .env
```

Add the database values using the format expected by Django `settings.py`.

Example:

```
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=your-supabase-host
DB_PORT=6543
```

Once this file exists, the Django container will connect to Supabase automatically.

---

# Running the Backend

Build and start the container:

```bash
docker compose up --build
```

When the container starts:

- Django connects to Supabase
- Migrations run automatically
- Database tables are created

The API will run at:

```
http://localhost:8000
```

---

# Populate the Database

After the container is running, open a shell inside the container.

```
docker exec -it <container-name> bash
```

Then run:

```
python manage.py refresh_ufc_data
```

This command:

- Scrapes UFC data
- Populates fighters
- Populates events
- Populates fights

After this step the database is fully initialized.

---

# Updating the Data

After new UFC events occur, update the database by running:

```
python manage.py refresh_ufc_data
```

This should typically be done **once per week**.

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

During development you need **two running processes**.

## Backend

```
docker compose up
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
