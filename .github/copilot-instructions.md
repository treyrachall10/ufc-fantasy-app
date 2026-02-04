# UFC Fantasy Codebase Instructions for AI Agents

## Architecture Overview

**Tech Stack**: Django 5.2 REST API (Python backend) + PostgreSQL + Docker Compose + React frontend (WIP)

### Core Data Model
The system has two distinct data domains:
- **Fight Data**: Scraped UFC statistics normalized through a multi-stage pipeline
  - `Fighters` → `FighterCareerStats` (one-to-one) → individual fight statistics
  - `Events` → `Fights` (one-to-many) → `FightStats` (per fighter) → `RoundStats` (per round)
  - Fantasy scoring derives from `RoundStats` via `RoundScore` and `FightScore` models
  
- **Fantasy Game Logic**: Multi-player league system with draft mechanics
  - `League` (container) → `LeagueMember` (users) → `Team` (owner has one per league)
  - `Roster` (slots by weight class) + `Draft` (draft order and picks)
  - Weight class mapping: STRAWWEIGHT through HEAVYWEIGHT plus FLEX slot

### Key Files
- **Models**: [backend/fantasy/models.py](backend/fantasy/models.py) (~293 lines) - defines all entities and relationships
- **Views/Endpoints**: [backend/api/views.py](backend/api/views.py) (~596 lines) - REST endpoints with transaction management
- **Serializers**: [backend/api/serializers.py](backend/api/serializers.py) (~509 lines) - nested serializers for complex entities
- **Data Pipeline**: [backend/scripts/parse_data.py](backend/scripts/parse_data.py) - normalizes raw UFC stats CSV files

## Developer Workflows

### Backend Development (Docker)
```bash
docker compose up --build          # First-time setup with rebuild
docker compose up                  # Subsequent runs
# Django runs at http://localhost:8000, auto-reloads on code changes
```

### Frontend Development
```bash
cd frontend/ufc-fantasy-frontend
npm start                          # Runs React dev server at http://localhost:3000
npm run build                      # Production build
npm test                           # Run tests
```
- Built with **React 18** + **TypeScript** + **TailwindCSS** + **MUI v7** (Material-UI)
- React Router for navigation (see routes in [src/App.tsx](frontend/ufc-fantasy-frontend/src/App.tsx))
- **TanStack React Query** for data fetching with caching and devtools
- Auth state managed via `AuthProvider` context ([auth/AuthProvider.tsx](frontend/ufc-fantasy-frontend/src/auth/AuthProvider.tsx))
- Key pages: HomePage, LeaguesPage, LeagueCreation, DraftLobbyPage, UserTeamPage, FightersListPage, AthleteStatsPage

### Database Migrations
```bash
# From inside container or with proper python env:
python backend/manage.py makemigrations
python backend/manage.py migrate
```

### Data Import
- Raw CSV files in `backend/data/raw/` (6 files from UFC Stats scraper)
- Processing script: `backend/scripts/parse_data.py` → normalized output to `backend/data/clean/`
- `db_population.py` loads cleaned data into database

## Project-Specific Patterns

### API Endpoints Pattern
Endpoints follow `action_resource` naming: `GetFighterProfileViewSet`, `CreateLeague`, etc.
- Use `@transaction.atomic` decorator for multi-model operations (see League creation in views.py)
- All user-scoped endpoints require `@permission_classes([IsAuthenticated])`
- Return Response objects with explicit status codes (201 for creation, 409 for conflicts)

### Serializers Pattern
Complex nested serializers use `source='*'` to denormalize related model data:
```python
# Example: FighterSerializer nests career stats and applies multiple serializers
record = RecordSerializer(source='*', read_only=True)  # Re-serializes FighterCareerStats into nested 'record'
```

### Data Type Conventions
- **Time**: Stored as integer seconds (converted from MM:SS format in parse_data.py)
- **Height/Reach**: Stored in total inches (converted from feet'inches" format)
- **Strikes**: Separated into `landed` and `attempted` columns (parse_data.py handles "X of Y" → two columns)

### Fantasy Scoring
- Per-round scoring via `RoundScore` (6 point categories from round_stats)
- Fight-level scoring via `FightScore` (aggregates rounds, adds win bonus, time bonus)
- Scoring logic in [backend/scripts/scoring.py](backend/scripts/scoring.py)

## Critical Dependencies & Integration Points

### External Packages
- **Authentication**: `django-allauth`, `dj-rest-auth`, `djangorestframework-simplejwt` (JWT token auth)
- **Database**: PostgreSQL 14 via Docker (psycopg3 driver), SQLite for local testing
- **Data**: pandas for CSV processing, requests + BeautifulSoup for scraping

### Environment Setup
- Settings in [backend/ufc_fantasy/settings.py](backend/ufc_fantasy/settings.py) - CORS enabled for all origins (dev only)
- Uses custom User model (`AbstractUser` in accounts/models.py)
- Site framework enabled (SITE_ID=1 required for allauth)
- Frontend API base: `http://localhost:8000` (configured in React environment)

## Frontend-Specific Patterns

### Authentication Flow
- JWT token stored in localStorage via `auth/auth.ts` utility functions
- `AuthProvider` wraps app and manages token/user state via React Context
- `ProtectedRoute` component restricts access to authenticated endpoints
- `authFetch` intercepts requests to add Authorization header
- Token refresh logic in auth module (uses `dj-rest-auth` endpoints)

### API Integration
- TanStack React Query (v5) handles data fetching, caching, and background updates
- Query keys follow pattern: `['resource', id]` (e.g., `['fighters', fighterId]`)
- Components use `useQuery`/`useMutation` hooks (not direct fetch calls)
- Devtools available in dev: `<ReactQueryDevtools />` in App.tsx

### Component Structure
- **pages/**: Route-level components (FightersListPage, LeagueDashboard, etc.)
- **components/**: Reusable UI components organized by feature (layout/, lists/, charts/, Draftcards/, etc.)
- **theme/**: MUI theme customization (colors, typography, spacing)
- **types/**: TypeScript interfaces for data models
- **auth/**: Authentication utilities and context providers

### Styling
- MUI components (Box, Button, Dialog, DataGrid, etc.) as primary UI library
- Tailwind CSS for utility classes (via `tailwind-merge` for conflict resolution)
- Emotion for styled-components if needed
- Highcharts and Recharts for data visualization

## Common Tasks

**Add a new API endpoint**:
1. Create view with `@api_view` decorator in [backend/api/views.py](backend/api/views.py)
2. Add serializer if needed to [backend/api/serializers.py](backend/api/serializers.py)
3. Register route in [backend/api/urls.py](backend/api/urls.py)
4. Test permissions and response format

**Add a database field**:
1. Update model in [backend/fantasy/models.py](backend/fantasy/models.py)
2. Create migration: `python manage.py makemigrations`
3. Review generated migration file in `fantasy/migrations/`
4. Apply: `python manage.py migrate`

**Debug a data issue**:
- Check raw CSV structure in `backend/data/raw/`
- Trace processing through [backend/scripts/parse_data.py](backend/scripts/parse_data.py) (prints applied transformations)
- Verify cleaned output in `backend/data/clean/`
- Query models directly in Django shell: `python manage.py shell`
