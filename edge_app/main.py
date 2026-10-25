
import asyncio
import math
import os
import time

from fastapi import FastAPI

app = FastAPI(title="Federated Edge Node")

NODE_NAME = os.getenv("NODE_NAME", "edge-node")
LATENCY_DELAY_MS = float(os.getenv("LATENCY_DELAY_MS", "0"))


def simulate_compute(duration_ms: int = 35):
    """Simulate CPU work for an edge analytics request."""
    end_time = time.perf_counter() + duration_ms / 1000.0

    while time.perf_counter() < end_time:
        _ = math.sqrt(12345.6789) * math.sin(9876.54)


@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "node": NODE_NAME,
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "node": NODE_NAME,
    }


@app.get("/process")
async def process_workload():
    start = time.perf_counter()

    # Simulate network latency without blocking the event loop.
    if LATENCY_DELAY_MS > 0:
        await asyncio.sleep(LATENCY_DELAY_MS / 1000.0)

    # Run the small CPU workload in a worker thread.
    await asyncio.to_thread(simulate_compute, 35)

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return {
        "status": "completed",
        "node": NODE_NAME,
        "latency_simulated_ms": LATENCY_DELAY_MS,
        "execution_time_ms": round(elapsed_ms, 2),
    }
