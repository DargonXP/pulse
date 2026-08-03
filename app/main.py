from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import admin, analytics, auth, campaigns, customers, dashboard, meta, recommendations, tools
from app.seed_data import seed

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Backend API for UpWise — a growth & loyalty platform for small offline businesses in Kazakhstan.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(meta.router)
app.include_router(tools.router)
app.include_router(campaigns.router)
app.include_router(customers.router)
app.include_router(analytics.router)
app.include_router(dashboard.router)
app.include_router(recommendations.router)
app.include_router(admin.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "app": settings.app_name}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
