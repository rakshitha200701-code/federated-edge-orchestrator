import random
from locust import HttpUser, task, between

class EdgeUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def process_request(self):
        params = {"mode": "dynamic", "payload": random.randint(100, 1000)}
        self.client.get("/process", params=params)