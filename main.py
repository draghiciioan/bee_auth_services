from fastapi import FastAPI


app = FastAPI(title="BeeConect Auth Service")


@app.get("/")
def read_root():
    return {"message": "BeeConect Auth Service is running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "auth-service"}
