from locust import HttpUser, task, between
import random

class GHGUser(HttpUser):
    # Simulate a user pausing between 1 to 5 seconds between actions
    wait_time = between(1, 5)

    def on_start(self):
        # Authenticate if necessary. We will assume public/test endpoints or mocked auth for this test.
        self.headers = {"Authorization": "Bearer test"}
        pass

    @task(3)
    def view_dashboard_stats(self):
        # Heavy aggregation endpoint
        self.client.get("/api/dashboard/stats?year=2024", headers=self.headers)

    @task(2)
    def view_intensity_stats(self):
        # Methane explorer / intensity stats
        self.client.get("/api/dashboard/intensity-stats?year=2024", headers=self.headers)

    @task(2)
    def view_facilities(self):
        # Fetching all facilities
        self.client.get("/api/facilities", headers=self.headers)

    @task(1)
    def view_satellite_layer(self):
        self.client.get("/api/satellite/sentinel5p/layer-config", headers=self.headers)
