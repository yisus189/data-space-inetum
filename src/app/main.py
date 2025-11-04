from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.routers import participants, publications, requests as reqs, contracts, transfers

def create_app() -> FastAPI:
    app = FastAPI(title="Data Space API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(participants.router, prefix="/participants", tags=["participants"])
    app.include_router(publications.router, prefix="/publications", tags=["publications"])
    app.include_router(reqs.router, prefix="/requests", tags=["requests"])
    app.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
    app.include_router(transfers.router, prefix="/transfers", tags=["transfers"])

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)# Content of main.py here
