"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analysis

app = FastAPI(
    title="Satellite Solar Environment Analyzer",
    version="3.0.0",
    description=(
        "Circular-orbit solar environment analysis with dual-wing solar array "
        "geometry, ideal and constrained Sun tracking, and power generation model."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://sat-solar-app.web.app",
        "https://sat-solar-app.firebaseapp.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
