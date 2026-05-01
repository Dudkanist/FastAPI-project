from fastapi import FastAPI

app = FastAPI(
    title="GeneVault API",
    description="API для хранения и анализа генетических последовательностей",
    version="0.1",
)

@app.get("/", tags=["Healthcheck"])
async def root():
    return {"message": "GeneVault API is running"}
