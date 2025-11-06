# UFC Fantasy App

**Dockerized Django backend and frontend (frontend not yet implemented)** for a UFC fantasy application.  
This project is built for full-stack development using containers — ready for local development, future frontend integration, and eventual deployment.

---

## **Prerequisites**

Make sure you have the following installed before running:

- Docker Desktop  
- Docker Compose  
- Visual Studio Code  
- VS Code Docker Extension (by Microsoft)

---

## **Local Development Setup**

# 1. Clone the Repository
git clone https://github.com/<your-username>/ufc-fantasy-app.git
cd ufc-fantasy-app

# 2. Build and Run Containers
docker compose up --build

# The app will run at:
http://localhost:8000

# 3. Verify the Setup
You should see this in the terminal:
"Django version 5.x, using settings 'ufc_fantasy.settings'
Starting development server at http://0.0.0.0:8000/"

Open your browser and go to:
http://localhost:8000

---

## **Stopping Containers**

# Stop and clean up containers
Ctrl + C
docker compose down

This stops the containers and removes them while keeping your database data in the persisted volume.

---

## **Production / VS Code Container Workflow**

If you’re using the VS Code Docker extension, you can work directly inside the running container without rebuilding each time.

# 1. Install the VS Code Docker Extension
Open VS Code → Extensions → Search "Docker" → Install (by Microsoft)

# 2. Start the Containers
docker compose up
# or, in Docker Desktop:
Open Docker Desktop → Containers → select "ufc-fantasy-app" → click "Start"

# 3. Attach to the Running Container
In VS Code:
- Open the Docker extension panel
- Expand Containers → select the "web" container (e.g., ufc-fantasy-app_web_1)
- Right-click → Attach Visual Studio Code

VS Code will open a new window directly inside the container’s environment.

Once attached:
- Edit Django code directly
- Run migrations or management commands inside the built-in terminal
- See code changes instantly (Django auto-reloads with StatReloader)

You do **not** have to rebuild after every change.

---

## **Long Term Plans**

- Implement a frontend (React or Angular) served through Nginx  
- Add user authentication and fantasy scoring logic  
- Deploy to production (AWS, Azure, or Docker Hub image)

---

## **Tech Stack**

| Component | Technology |
|------------|-------------|
| Backend | Django 5.x |
| Database | PostgreSQL 14 |
| Frontend | To be implemented |
| Containerization | Docker + Docker Compose |
| Editor Integration | VS Code Docker Extension |

---

## **Summary**

This project is designed for collaborative, containerized development.  
Anyone can clone, build, and run with one command — and use VS Code’s Docker tools to make direct changes inside the container environment.