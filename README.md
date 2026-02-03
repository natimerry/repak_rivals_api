# Marvel Rivals Skin API

A FastAPI REST API that scrapes Marvel Rivals character skin data from the Fandom Wiki with smart caching and auto-refresh.

## What It Does

Provides structured access to Marvel Rivals skin data through a REST API:
- Scrapes all heroes and their skins (regular + recolor variants)
- Smart caching with 2-hour TTL and 12-hour auto-refresh
- Real-time progress tracking for cache updates
- Fast lookups by character, skin ID, or name pattern

## Endpoints

```
GET  /health                    # Health check
GET  /skins                     # All cached skins
GET  /character/{name}          # Skins for specific character
GET  /skin/{id}                 # Skin by ID
GET  /skin/name/{pattern}       # Search by name
POST /refresh                   # Trigger manual refresh
GET  /refresh/status            # Check refresh progress
```

### Example Response
```json
{
  "name": "Adam Warlock",
  "url": "https://marvelrivals.fandom.com/wiki/Cosmic_Warlock",
  "skinid": 1046302,
  "skin_name": "Cosmic Warlock"
}
```

## Setup

```bash
git clone https://github.com/natimerry/repak_rivals_api.git
cd repak_rivals_api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Requirements:** Python 3.10+, FastAPI, BeautifulSoup4, APScheduler

**First run:** Cache auto-populates on startup (takes 4-6 minutes). Access docs at `http://localhost:8000/docs`

## Configuration

Modify in source:
```python
# scraper.py
CACHE_TTL_SECONDS = 2 * 60 * 60  # Cache lifetime

# main.py  
scheduler.add_job(..., hours=12)  # Auto-refresh interval
```

## Deployment

Production server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Optional Docker:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Known Issues

- Initial cache population takes 4-6 minutes
- Wiki CSS changes may break scraper

## Roadmap

- Webhook notifications for new skins
- Provide skin matching patterns for repak-rivals to patch `.uasset` files
- Rate limiting and API authentication
- Historical skin data tracking

## License

MIT

**Note:** Not affiliated with NetEase Games or Marvel Entertainment. Data sourced from [Marvel Rivals Fandom Wiki](https://marvelrivals.fandom.com).

***
