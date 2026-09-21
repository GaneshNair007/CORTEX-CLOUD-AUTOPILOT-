"""Server-side bearer roles. Missing configuration always denies mutations."""
import hmac
import os
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse

READ_POSTS = {"/api/rag/retrieve", "/api/v1/evidence/retrieve", "/api/topology/blast-radius",
              "/api/twin/simulate", "/api/forecasting/predict", "/api/optimizer", "/api/optimizer/solve"}
ADMIN_ROUTES = {"/api/cortex/autonomy", "/api/cortex/kill-switch", "/api/events/clear"}
PUBLIC_ROUTES = {"/", "/healthz", "/readyz", "/api/ping", "/api/health", "/docs", "/openapi.json", "/redoc"}


def role_for(authorization: str) -> str | None:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 4096:
        return None
    for role in ("admin", "operator", "viewer"):
        configured = os.environ.get(f"CORTEX_{role.upper()}_TOKEN", "")
        if configured and len(configured) >= 32 and hmac.compare_digest(configured, token):
            return role
    return None


def install_security(app) -> None:
    @app.middleware("http")
    async def authorize(request: Request, call_next):
        correlation_id = uuid.uuid4().hex
        request.state.correlation_id = correlation_id
        role = role_for(request.headers.get("authorization", ""))
        request.state.actor = role or "anonymous"
        path = request.url.path.rstrip("/") or "/"
        mutating = request.method not in {"GET", "HEAD", "OPTIONS"} and path not in READ_POSTS
        private_reads = os.environ.get("CORTEX_PUBLIC_READS", "false").lower() != "true"
        required = "admin" if path in ADMIN_ROUTES else "operator" if mutating else "viewer"
        must_auth = request.method != "OPTIONS" and (mutating or (private_reads and path not in PUBLIC_ROUTES))
        ranks = {None: 0, "viewer": 1, "operator": 2, "admin": 3}
        if must_auth and ranks[role] < ranks[required]:
            response = JSONResponse(status_code=401 if role is None else 403,
                content={"error": "AUTHENTICATION_REQUIRED" if role is None else "INSUFFICIENT_ROLE",
                         "detail": f"{required.capitalize()} access required", "correlation_id": correlation_id})
        else:
            response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
