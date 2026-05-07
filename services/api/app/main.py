from fastapi import FastAPI

from app.routes import city_guide, collaboration, health, inspirations, journals, plans, ws

app = FastAPI(title="LocalPlan Agent API")

app.include_router(health.router)
app.include_router(plans.router)
app.include_router(collaboration.router)
app.include_router(journals.router)
app.include_router(inspirations.router)
app.include_router(city_guide.router)
app.include_router(ws.router)
