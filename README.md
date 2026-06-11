# ScentScience

A machine learning platform that takes a cologne/perfume as input and predicts **35+ contextual performance outputs** — from longevity and sillage to season fit, climate performance, skin type compatibility, and occasion scoring. Powered by XGBoost and the Claude API for natural language summaries.

---

## Architecture

```
scentscience/
├── backend/          FastAPI + PostgreSQL + XGBoost
├── frontend/         React + Recharts dashboard
├── notebooks/        EDA and model training
└── docker-compose.yml
```

## Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node 18+
- PostgreSQL 15+
- Docker (optional)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Copy env and fill in values
cp ../.env.example .env

# Run database migrations
python -c "from models.database import init_db; import asyncio; asyncio.run(init_db())"

# Seed initial data
python -c "from scripts.seed import seed_all; import asyncio; asyncio.run(seed_all())"

# Train initial models
python -c "from ml.model import train_all_models; train_all_models()"

# Start server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### Docker (Full Stack)

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/predict` | Predict scores for a perfume |
| GET | `/api/perfumes` | Search/list perfumes |
| GET | `/api/perfumes/{id}` | Get single perfume |
| GET | `/api/notes` | List all notes |
| GET | `/health` | Health check |

### Predict Example

```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "perfume_name": "Sauvage",
    "brand": "Dior",
    "context": {
      "skin_type": "dry",
      "season": "summer",
      "time_of_day": "evening"
    }
  }'
```

## Deploy to Railway

1. Install Railway CLI: `npm i -g @railway/cli`
2. `railway login`
3. `railway link` (select your project)
4. Set environment variables in Railway dashboard
5. `railway up`

Or connect the GitHub repo in the Railway dashboard for auto-deploys.

## Improving the Model

1. **More data** — Run `python backend/scrapers/fragrantica.py` to scrape more perfumes
2. **More notes** — Expand `notes_chemistry.json` beyond the initial 50
3. **User feedback** — Collect ratings via the `UserReview` table to retrain
4. **Hyperparameter tuning** — Run `notebooks/03_model_training.ipynb`
5. **Ensemble** — Blend XGBoost with LightGBM for better accuracy

## License

MIT
