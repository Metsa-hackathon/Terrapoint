from fastapi import FastAPI


app = FastAPI()


@app.get("/api/diagnostic")
def diagnostic():
    try:
        import api.index  # noqa: F401
    except Exception as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "message": str(exc)[:300],
        }
    return {"ok": True}
