import time
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

RATE_LIMIT = 5
WINDOW_SECONDS = 60

clients: dict[str, dict] = {}

@app.api_route(
    "/{path:path}",
    methods={"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
)
async def proxy(request: Request, path: str):
    client_ip = request.client.host
    
    print("client_ip is " + str(client_ip))
    
    if not is_allowed(client_ip_addr=client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )
    
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


def is_allowed(client_ip_addr: str) -> bool:
    now = time.time()
    
    client_data = clients.get(client_ip_addr)
    
    if client_data is None:
        clients[client_ip_addr] = {
            "count": 1,
            "window_start": now
        }
        
        return True
    
    if now - client_data["window_start"] >= WINDOW_SECONDS:
        client_data["count"] = 1
        client_data["window_start"] = now
        
        return True
    
    if client_data["count"] >= RATE_LIMIT:
        return False
        
    client_data["count"] += 1
    
    return True