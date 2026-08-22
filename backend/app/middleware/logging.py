import time

from app.core.logging import get_logger, new_request_id, request_id_var, tenant_id_var, user_id_var

logger = get_logger(__name__)


class RequestLoggingMiddleware:
    """
    Pure ASGI middleware (not BaseHTTPMiddleware) so client disconnect
    cancellation propagates correctly and DB session cleanup can finish.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-request-id":
                request_id = value.decode()
                break
        if not request_id:
            request_id = new_request_id()
        request_id_var.set(request_id)

        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            path = scope.get("path", "")
            method = scope.get("method", "")
            logger.info(
                "request_completed",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
                tenant_id=tenant_id_var.get(),
                user_id=user_id_var.get(),
            )
