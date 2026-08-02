from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse


def register_error_handlers(app: FastAPI):
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        # Let FastAPI handle HTTPException normally (401, 403, 404, etc.)
        if isinstance(exc, HTTPException):
            raise exc
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )
