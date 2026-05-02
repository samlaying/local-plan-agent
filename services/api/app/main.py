from fastapi import FastAPI

from services.api.app.routes import health

app = FastAPI(title="LocalPlan Agent API")

app.include_router(health.router)
