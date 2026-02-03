import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import BackgroundTasks, FastAPI, HTTPException

app = FastAPI()

CACHE_DIR = Path("cache")

# Global state for cache refresh
cache_status = {
    "is_refreshing": False,
    "last_refresh": None,
    "progress": {"current": 0, "total": 0},
}


def load_all_skins() -> List[dict]:
    """Load all skins from cache files"""
    all_skins = []

    if not CACHE_DIR.exists():
        return all_skins

    for cache_file in CACHE_DIR.glob("skins_*.json"):
        try:
            with cache_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                payload = data.get("payload", [])
                all_skins.extend(payload)
        except (json.JSONDecodeError, KeyError):
            continue

    return all_skins


def refresh_cache_background():
    """Refresh cache in background"""
    global cache_status

    if cache_status["is_refreshing"]:
        print("Cache refresh already in progress, skipping...")
        return

    try:
        cache_status["is_refreshing"] = True
        print(f"Starting cache refresh at {datetime.now()}")

        # Import here to avoid circular imports
        from your_scraper_file import get_hero_skins, get_heroes

        heroes = get_heroes()
        cache_status["progress"]["total"] = len(heroes)

        for i, hero in enumerate(heroes):
            cache_status["progress"]["current"] = i + 1
            print(f"Processing {i + 1}/{len(heroes)}: {hero.name}")
            get_hero_skins(hero)  # This will cache the skins

        cache_status["last_refresh"] = datetime.now().isoformat()
        print(f"Cache refresh completed at {datetime.now()}")
    except Exception as e:
        print(f"Error during cache refresh: {e}")
    finally:
        cache_status["is_refreshing"] = False
        cache_status["progress"] = {"current": 0, "total": 0}


# Initialize scheduler
scheduler = BackgroundScheduler()


@app.on_event("startup")
async def startup_event():
    """Start the scheduler on app startup"""
    # Schedule cache refresh every 12 hours
    scheduler.add_job(
        refresh_cache_background,
        "interval",
        hours=12,
        id="cache_refresh",
        replace_existing=True,
    )
    scheduler.start()

    print("Scheduler started - cache will refresh every 12 hours")

    # Optional: Do an initial refresh on startup if cache is empty
    if not load_all_skins():
        print("Cache is empty, doing initial refresh...")
        refresh_cache_background()


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the scheduler gracefully"""
    scheduler.shutdown()
    print("Scheduler shutdown")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/skins")
def get_all_skins():
    """Get all skins from cache"""
    skins = load_all_skins()

    if not skins:
        return {
            "message": "No skins in cache. Trigger /refresh to populate cache.",
            "skins": [],
        }

    return skins


@app.post("/refresh")
def trigger_refresh(background_tasks: BackgroundTasks):
    """Trigger cache refresh manually"""
    global cache_status

    if cache_status["is_refreshing"]:
        return {"message": "Cache refresh already in progress", "status": cache_status}

    background_tasks.add_task(refresh_cache_background)

    return {
        "message": "Cache refresh started in background",
        "status": "Check /refresh/status for progress",
    }


@app.get("/refresh/status")
def get_refresh_status():
    """Get current refresh status"""
    next_run = None
    job = scheduler.get_job("cache_refresh")
    if job:
        next_run = job.next_run_time.isoformat() if job.next_run_time else None

    return {**cache_status, "next_scheduled_refresh": next_run}


@app.get("/character/{character_name}")
def get_character_skins(character_name: str):
    """Get all skins for a specific character"""
    all_skins = load_all_skins()
    character_skins = [
        skin
        for skin in all_skins
        if skin.get("name", "").lower() == character_name.lower()
    ]

    if not character_skins:
        raise HTTPException(
            status_code=404, detail=f"Character '{character_name}' not found"
        )

    return {"character": character_name, "skins": character_skins}


@app.get("/skin/{skin_id}")
def get_skin_by_id(skin_id: int):
    """Get skin details by skin ID"""
    all_skins = load_all_skins()

    for skin in all_skins:
        if skin.get("skinid") == skin_id:
            return skin

    raise HTTPException(status_code=404, detail=f"Skin with ID {skin_id} not found")


@app.get("/skin/name/{skin_name}")
def get_skin_by_name(skin_name: str):
    """Get skin details by skin name"""
    all_skins = load_all_skins()

    matching_skins = [
        skin
        for skin in all_skins
        if skin_name.lower() in skin.get("skin_name", "").lower()
    ]

    if not matching_skins:
        raise HTTPException(
            status_code=404, detail=f"No skins found matching '{skin_name}'"
        )

    return matching_skins
