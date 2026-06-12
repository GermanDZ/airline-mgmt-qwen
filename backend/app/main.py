"""FastAPI application entry point.

Scaffold for Sprint 0: auth and audit logging routes will be mounted here.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Airline Management System",
    description="Flight Ops, Crew Mgmt & Dashboard — MVP",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint for CI and monitoring."""
    return {"status": "ok"}
