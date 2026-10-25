
import os
import time
import requests

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Federated Edge Orchestrator")

EDGE_NODES = {
    "edge-chennai": {
        "url": "http://edge-chennai:8000",
        "latency": 10,
        "primary": True,
    },
    "edge-bangalore": {
        "url": "http://edge-bangalore:8000",
        "latency": 25,
        "primary": False,
    },
    "edge-hyderabad": {
        "url": "http://edge-hyderabad:8000",
        "latency": 35,
        "primary": False,
    },
}

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus:9090",
)

SESSION = requests.Session()


def is_node_healthy(node_name: str) -> bool:
    """Check whether an edge node is reachable."""
    try:
        response = SESSION.get(
            f"{EDGE_NODES[node_name]['url']}/health",
            timeout=0.5,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_node_cpu(node_name: str) -> float:
    """
    Read approximate container CPU usage from Prometheus.
    Returns a conservative default if metrics are unavailable.
    """
    query = (
        '100 * sum(rate(container_cpu_usage_seconds_total'
        '{container_label_com_docker_compose_service="'
        + node_name
        + '", image!=""}[1m]))'
    )

    try:
        response = SESSION.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=0.7,
        )
        response.raise_for_status()

        results = response.json().get("data", {}).get("result", [])

        if results:
            return max(0.0, float(results[0]["value"][1]))
    except (requests.RequestException, ValueError, KeyError, TypeError):
        pass

    # Neutral fallback when monitoring data isn't available.
    return 20.0


def compute_fitness(cpu: float, latency: float) -> float:
    """
    Higher score means a more attractive candidate.
    CPU is measured as a percentage of one CPU core's capacity.
    """
    cpu = min(max(cpu, 0.0), 100.0)

    return (
        0.7 * (100.0 - cpu)
        - 0.3 * latency
    )


def forward_to_node(node_name: str):
    """Forward a workload and return a consistent response."""
    response = SESSION.get(
        f"{EDGE_NODES[node_name]['url']}/process",
        timeout=3,
    )
    response.raise_for_status()

    result = response.json()
    result["routed_by"] = "orchestrator"
    result["assigned_node"] = node_name

    return result


@app.get("/")
def root():
    return {
        "project": "Federated Edge Orchestrator",
        "available_modes": ["static", "dynamic"],
        "nodes": list(EDGE_NODES.keys()),
    }


@app.get("/health")
def orchestrator_health():
    return {"status": "healthy", "service": "orchestrator"}


@app.get("/nodes")
def get_nodes():
    """Expose current node reachability for a dashboard."""
    return {
        name: {
            "healthy": is_node_healthy(name),
            "primary": info["primary"],
            "simulated_latency_ms": info["latency"],
        }
        for name, info in EDGE_NODES.items()
    }


@app.api_route("/process", methods=["GET", "POST"])
def route_workload(
    mode: str = Query(default="dynamic", pattern="^(dynamic|static)$")
):
    # STATIC: always send requests to Chennai.
    # Never fail over; this is the baseline for comparison.
    if mode == "static":
        try:
            result = forward_to_node("edge-chennai")
            result["mode"] = "static"
            return result
        except requests.RequestException:
            raise HTTPException(
                status_code=503,
                detail="Static routing failed: Chennai is unavailable",
            )

    # DYNAMIC: check reachability before scoring candidates.
    candidates = []

    for name, info in EDGE_NODES.items():
        if not is_node_healthy(name):
            continue

        cpu = get_node_cpu(name)
        score = compute_fitness(cpu, info["latency"])

        candidates.append({
            "name": name,
            "score": score,
            "cpu_percent": cpu,
            "latency_ms": info["latency"],
        })

    # Prefer the highest-scoring available node.
    candidates.sort(key=lambda item: item["score"], reverse=True)

    # Try other available nodes if a node dies between health check
    # and workload forwarding.
    for candidate in candidates:
        try:
            result = forward_to_node(candidate["name"])
            result["mode"] = "dynamic"
            result["fitness_score"] = round(candidate["score"], 2)
            result["observed_cpu_percent"] = round(
                candidate["cpu_percent"], 2
            )
            return result
        except requests.RequestException:
            continue

    return JSONResponse(
        status_code=503,
        content={
            "status": "failed",
            "mode": "dynamic",
            "detail": "No available edge nodes",
        },
    )
