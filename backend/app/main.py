"""
Entry point for the Electoral Count System API.
TODO: mount routers once each service is implemented.
"""
from fastapi import FastAPI

app = FastAPI(
    title="Sistema de Cómputo Electoral Bolivia",
    version="0.1.0",
    description="API para los pipelines RRV y Cómputo Oficial.",
)

# TODO (MOLLO / Ferrufino / Sanabria): include rrv_routes.router
# from app.api.rrv_routes import router as rrv_router
# app.include_router(rrv_router, prefix="/api/rrv", tags=["RRV"])

# TODO (Erick Diaz): include oficial_routes.router
# from app.api.oficial_routes import router as oficial_router
# app.include_router(oficial_router, prefix="/api/oficial", tags=["Oficial"])

# TODO (Erick Diaz): include dashboard_routes.router
# from app.api.dashboard_routes import router as dashboard_router
# app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

# TODO (Escobar): include health_routes.router
# from app.api.health_routes import router as health_router
# app.include_router(health_router, prefix="/api/health", tags=["Health"])


@app.get("/")
async def root():
    return {"message": "Sistema de Cómputo Electoral - API activa"}
