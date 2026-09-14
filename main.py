import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from config import settings

app = FastAPI()

HOP_BY_HOP_HEADERS = {
    "connection",
    "content-encoding",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}

@app.api_route(
    "/{path:path}",
    methods={"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
)
async def proxy(request: Request, path: str):
    target_url = f"{settings.backend_url.rstrip('/')}/{path.lstrip('/')}"

    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    request_headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in HOP_BY_HOP_HEADERS
    }

    try:
        async with httpx.AsyncClient() as client:
            backend_response = await client.request(
                method=request.method,
                url=target_url,
                headers=request_headers,
                content=await request.body(),
            )
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach the backend service.",
        ) from error

    response_headers = {
        name: value
        for name, value in backend_response.headers.items()
        if name.lower() not in HOP_BY_HOP_HEADERS
    }

    return Response(
        content=backend_response.content,
        status_code=backend_response.status_code,
        headers=response_headers,
    )
