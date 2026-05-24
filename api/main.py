from fastapi import FastAPI

app = FastAPI(
    title="Scrapyard API",
    description="Web Scraper as a Service — платформа для распределенного парсинга",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "scrapyard-api"}