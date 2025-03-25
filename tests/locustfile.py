
from locust import HttpUser, TaskSet, task, between

class ShortLinkTasks(TaskSet):

    def on_start(self):
        # Регистрация пользователя
        # response = self.client.post("/auth/register", json={"email": "test@example.com", "password": "password123"})
        # assert response.status_code == 201

        # Авторизация пользователя
        response = self.client.post("/auth/jwt/login", data={"username": "test@example.com", "password": "password123"})
        print(response.text)
        assert response.status_code == 200
        self.token = response.json()["access_token"]

    @task
    def shorten_url(self):
        response = self.client.post("/links/shorten", json={"original_url": "http://example.com"}, headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200

    @task
    def search_link(self):
        response = self.client.get("/links/search", params={"original_url": "example.com"}, headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200

    @task
    def redirect_url(self):
        response = self.client.post("/links/shorten", json={"original_url": "http://example.com"}, headers={"Authorization": f"Bearer {self.token}"})
        short_code = response.json()["short_url"].split("/")[-1]
        response2 = self.client.get(f"/links/{short_code}", allow_redirects=False)
        print(response2.text)
        assert response2.status_code == 307

    @task
    def delete_link(self):
        response = self.client.post("/links/shorten", json={"original_url": "http://example.com"}, headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        if response.status_code == 200:
            short_code = response.json()["short_url"].split("/")[-1]
            self.client.delete(f"/links/{short_code}", headers={"Authorization": f"Bearer {self.token}"})

    @task
    def update_link(self):
        response = self.client.post("/links/shorten", json={"original_url": "http://example.com"}, headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        if response.status_code == 200:
            short_code = response.json()["short_url"].split("/")[-1]
            self.client.put(f"/links/{short_code}", json={"original_url": "http://newexample.com"}, headers={"Authorization": f"Bearer {self.token}"})

    @task
    def link_stats(self):
        response = self.client.post("/links/shorten", json={"original_url": "http://example.com"}, headers={"Authorization": f"Bearer {self.token}"})
        assert response.status_code == 200
        if response.status_code == 200:
            short_code = response.json()["short_url"].split("/")[-1]
            self.client.get(f"/links/{short_code}/stats", headers={"Authorization": f"Bearer {self.token}"})

class WebsiteUser(HttpUser):
    tasks = [ShortLinkTasks]
    wait_time = between(1, 5)