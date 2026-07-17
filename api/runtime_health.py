from fastapi import FastAPI


app = FastAPI()


@app.get("/api/runtime-health")
def runtime_health():
    return {"status": "ok"}
