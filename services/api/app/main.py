from fastapi import FastAPI

from services.api.app.routes import collaboration, health, plans

app = FastAPI(title="LocalPlan Agent API")

app.include_router(health.router)
app.include_router(plans.router)
app.include_router(collaboration.router)
