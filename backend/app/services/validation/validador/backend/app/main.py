from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Sistema Nacional de Cómputo Electoral - Bolivia",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes (each integrante registers their own router) ──────────────────────
# from app.api import rrv_routes, oficial_routes, dashboard_routes
# app.include_router(rrv_routes.router, prefix="/api/rrv", tags=["RRV"])
# app.include_router(oficial_routes.router, prefix="/api/oficial", tags=["Oficial"])
# app.include_router(dashboard_routes.router, prefix="/api/dashboard", tags=["Dashboard"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "backend"}


@app.get("/api/health/clusters")
async def health_clusters():
    # Escobar conectará las bases aquí
    return {
        "mongo": "pending",
        "postgres": "pending",
    }
