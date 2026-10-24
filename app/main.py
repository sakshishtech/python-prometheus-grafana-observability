
import time
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Observability Demo API")

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["endpoint"],
)

IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of requests currently being processed",
)


@app.middleware("http")
async def track_requests(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    endpoint = request.url.path
    start = time.perf_counter()
    IN_PROGRESS.inc()

    try:
        response = await call_next(request)
        REQUESTS.labels(
            request.method, endpoint, str(response.status_code)
        ).inc()
        return response
    except Exception:
        REQUESTS.labels(request.method, endpoint, "500").inc()
        raise
    finally:
        REQUEST_DURATION.labels(endpoint).observe(time.perf_counter() - start)
        IN_PROGRESS.dec()


@app.get("/")
def home():
    return {"message": "Observability demo is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/simulate-error")
def simulate_error():
    return Response(
        content='{"error":"simulated failure"}',
        status_code=500,
        media_type="application/json",
    )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
