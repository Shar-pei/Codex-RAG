from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def create_query_validation_exception_handler():
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        if request.url.path.endswith("/query/data"):
            error_details = []
            for error in exc.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                error_details.append(f"{field_path}: {error['msg']}")

            error_message = "; ".join(error_details)
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failure",
                    "message": f"Validation error: {error_message}",
                    "data": {},
                    "metadata": {},
                },
            )

        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    return validation_exception_handler
