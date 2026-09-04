from fastapi import FastAPI

app = FastAPI(title="Groww Smart Watchlist API")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "watchlist-engine"}