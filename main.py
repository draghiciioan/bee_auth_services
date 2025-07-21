from fastapi import FastAPI

from routers import auth as auth_router


app = FastAPI(title="BeeConect Auth Service")


@app.get("/")
def read_root():
    return {"message": "BeeConect Auth Service is running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "auth-service"}


app.include_router(auth_router.router)
