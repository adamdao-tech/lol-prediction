# LoL Predictor

Internal self-hosted LoL esports prediction application for a small group of users.

## O projektu

Interní webová aplikace pro predikci zápasů League of Legends. Aplikace stahuje data z PandaScore API, umožňuje import odds a zobrazuje predikce výsledků zápasů.

**Funkce:**
- Dashboard nadcházejících LoL esports zápasů
- Detail zápasu s predikcemi a odds
- Import bookmaker kurzů přes CSV
- Automatická synchronizace dat z PandaScore API
- REST API s dokumentací (Swagger UI)

---

## Požadavky

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/install/) v2+
- Git

---

## Rychlý start (lokálně na Ubuntu)

### 1. Instalace Dockeru (jednorázově)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin git

# Přidej sebe do docker skupiny (nepotřebuješ sudo před každým příkazem)
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Klonování

```bash
git clone https://github.com/adamdao-tech/lol-prediction.git
cd lol-prediction
```

### 3. Konfigurace

```bash
cp .env.example .env
nano .env
# Nastav PANDASCORE_API_KEY (registrace zdarma na https://pandascore.co)
# Změň ALLOWED_USERS — výchozí: admin/changeme
# Změň SECRET_KEY na náhodný řetězec
```

### 4. Spuštění

```bash
docker compose up --build
```

### 5. Aplikace běží na:

| Služba | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API dokumentace | http://localhost:8000/docs |

**Přihlášení:** výchozí `admin` / `changeme` (nastav v `.env` → `ALLOWED_USERS`)

---

## Manuální spuštění migrací

Pokud potřebuješ spustit migrace ručně (backend kontejner musí běžet):

```bash
docker compose exec backend alembic upgrade head
```

---

## Užitečné příkazy

```bash
# Zastavit vše
docker compose down

# Zastavit a smazat databázi (čistý start)
docker compose down -v

# Zobrazit logy backendu
docker compose logs -f backend

# Manuální sync zápasů
curl -u admin:changeme -X POST http://localhost:8000/api/admin/sync/matches

# Manuální sync lig
curl -u admin:changeme -X POST http://localhost:8000/api/admin/sync/leagues

# Health check
curl http://localhost:8000/health

# Zobrazit posledních 100 ingestion logů
curl -u admin:changeme http://localhost:8000/api/admin/ingestion-logs
```

---

## Struktura projektu

```
lol-prediction/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   └── app/
│       ├── main.py              # FastAPI app, lifespan, auth
│       ├── config.py            # Pydantic settings
│       ├── database.py          # SQLAlchemy async engine
│       ├── scheduler.py         # APScheduler jobs
│       ├── models/              # SQLAlchemy modely
│       ├── schemas/             # Pydantic response schemas
│       ├── api/
│       │   ├── router.py
│       │   └── endpoints/       # matches, teams, leagues, predictions, odds, admin
│       ├── ingestion/           # PandaScore client + sync funkce
│       └── utils/
│           └── logging.py
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── App.tsx
        ├── api/client.ts        # Axios instance + API volání
        ├── pages/
        │   ├── Dashboard.tsx
        │   └── MatchDetail.tsx
        └── components/
            ├── MatchCard.tsx
            ├── Navbar.tsx
            └── LoadingSpinner.tsx
```

---

## Datové zdroje

- **PandaScore API** — primární zdroj dat o zápasech, týmech a ligách
  - Registrace: https://pandascore.co
  - Dokumentace: https://developers.pandascore.co
  - Free tier: dostupný pro testování
- **Ruční import odds** — CSV upload přes `/api/odds/import`

---

## API přehled

| Metoda | Endpoint | Popis |
|--------|----------|-------|
| GET | `/health` | Health check (bez auth) |
| GET | `/api/matches/upcoming` | Nadcházející zápasy |
| GET | `/api/matches/finished` | Dokončené zápasy |
| GET | `/api/matches/{id}` | Detail zápasu |
| GET | `/api/teams` | Seznam týmů |
| GET | `/api/teams/{id}` | Detail týmu |
| GET | `/api/leagues` | Seznam lig |
| GET | `/api/predictions` | Historie predikcí |
| POST | `/api/predictions/{match_id}/generate` | Generuj predikci |
| POST | `/api/odds/import` | Import odds z CSV |
| GET | `/api/admin/health` | Admin health check |
| GET | `/api/admin/ingestion-logs` | Ingestion logy |
| POST | `/api/admin/sync/matches` | Manuální sync zápasů |
| POST | `/api/admin/sync/leagues` | Manuální sync lig |
| POST | `/api/admin/sync/teams` | Manuální sync týmů |

Kompletní dokumentace: http://localhost:8000/docs

### Import odds CSV

Formát souboru:
```csv
match_pandascore_id,bookmaker,team1_odds,team2_odds,snapshot_at
12345,Bet365,1.85,2.10,2024-06-01T14:00:00Z
```

```bash
curl -u admin:changeme -X POST http://localhost:8000/api/odds/import \
  -F "file=@odds.csv"
```

---

## Autentizace

Aplikace používá HTTP Basic Auth. Credentials se nastavují v `.env`:

```
ALLOWED_USERS=[{"username":"admin","password":"changeme"},{"username":"user2","password":"pass2"}]
```

Frontend ukládá credentials do `localStorage`:
```javascript
localStorage.setItem('lol_username', 'admin')
localStorage.setItem('lol_password', 'changeme')
```

---

## Roadmapa

### Fáze 1 — MVP (tato verze)
- [x] Projekt scaffold (Docker, DB, backend, frontend)
- [x] Databázové schéma (12 tabulek)
- [x] Ingestion z PandaScore API (ligy, týmy, zápasy)
- [x] APScheduler (automatická synchronizace)
- [x] REST API (matches, teams, leagues, predictions, odds, admin)
- [x] Frontend dashboard + detail zápasu
- [x] Import odds z CSV
- [x] HTTP Basic Auth

### Fáze 2 — Predikční model
- [ ] Baseline ML model (winner/kills/duration)
- [ ] Feature engineering (Elo, form, head-to-head)
- [ ] Reálné generování predikcí
- [ ] Edge kalkulace (model prob vs implied prob)

### Fáze 3 — Draft & pokročilé funkce
- [ ] Draft parser z API
- [ ] Manuální draft builder v UI
- [ ] Draft-adjusted predikce
- [ ] OCR screenshotu draftu

### Fáze 4 — Admin & monitoring
- [ ] Kompletní admin UI
- [ ] Monitoring (Grafana/Prometheus)
- [ ] Export CSV/JSON
- [ ] Watchlist oblíbených lig/týmů