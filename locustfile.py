
import os

from locust import HttpUser, task, between

# Select one mode per test run.
# Allowed values: dynamic or static.
TEST_MODE = os.getenv("TEST_MODE", "dynamic").lower()

if TEST_MODE not in {"dynamic", "static"}:
    raise ValueError("TEST_MODE must be dynamic or static")


class EdgeUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task
    def send_workload(self):
        self.client.get(
            f"/process?mode={TEST_MODE}",
            name=f"/process [{TEST_MODE}]",
        )
