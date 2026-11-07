import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from patient.api.routes import router as patient_router
from auth.routes import router as auth_router

from auth import models as auth_models  # noqa: F401
from patient.models import patient_models  # noqa: F401

from patient.models.database import init_db


app = FastAPI(
    title="Lord Diagnostics AI API",
    description="Backend API for the RAG Assistant",
)


@app.on_event("startup")
def startup_event():
    init_db()


# =========================================================
# CORS
# =========================================================

cors_env = os.getenv("ALLOWED_ORIGINS", "")
custom_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]

default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://medora-frontend.onrender.com",
]

allowed_origins = list(set(default_origins + custom_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Existing Healthcare API
# =========================================================

app.include_router(
    api_router,
    prefix="/api",
)


# =========================================================
# Authentication
# =========================================================

app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"],
)


# =========================================================
# Patient Intelligence Layer
# =========================================================

app.include_router(
    patient_router,
    prefix="/api/patient",
    tags=["Patient Intelligence Layer"],
)


if __name__ == "__main__":
    import uvicorn

    port = int(
        os.getenv(
            "PORT",
            8000,
        )
    )

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )