"""API tests. They use a temporary SQLite database so they run fast without Docker.

Run with:  pytest -v        (or: python -m unittest -v)
"""

import os
import tempfile
import unittest

from app import create_app


class TasksApiTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = create_app({"DATABASE_URL": f"sqlite:///{self.db_path}", "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        os.remove(self.db_path)

    def _create(self, title="Buy milk"):
        return self.client.post("/tasks", json={"title": title})

    # ---------- General ----------

    def test_index(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["app"], "tasks-api")

    def test_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), {"status": "ok", "database": "up"})

    # ---------- Create / list ----------

    def test_list_starts_empty(self):
        self.assertEqual(self.client.get("/tasks").get_json(), [])

    def test_create_task(self):
        res = self._create("Learn Docker")
        self.assertEqual(res.status_code, 201)
        body = res.get_json()
        self.assertEqual(body["title"], "Learn Docker")
        self.assertFalse(body["done"])
        self.assertIn("id", body)
        self.assertIn("created_at", body)

    def test_created_tasks_are_listed(self):
        self._create("one")
        self._create("two")
        titles = [t["title"] for t in self.client.get("/tasks").get_json()]
        self.assertEqual(titles, ["one", "two"])

    def test_create_requires_title(self):
        self.assertEqual(self.client.post("/tasks", json={}).status_code, 400)
        self.assertEqual(self.client.post("/tasks", json={"title": "   "}).status_code, 400)

    def test_create_rejects_long_title(self):
        self.assertEqual(self._create("x" * 201).status_code, 400)

    def test_create_rejects_non_json(self):
        res = self.client.post("/tasks", data="not json", content_type="text/plain")
        self.assertEqual(res.status_code, 400)

    # ---------- Read / update / delete ----------

    def test_get_task(self):
        task_id = self._create().get_json()["id"]
        res = self.client.get(f"/tasks/{task_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["title"], "Buy milk")

    def test_get_missing_task(self):
        self.assertEqual(self.client.get("/tasks/999").status_code, 404)

    def test_mark_done(self):
        task_id = self._create().get_json()["id"]
        res = self.client.patch(f"/tasks/{task_id}", json={"done": True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["done"])
        self.assertTrue(self.client.get(f"/tasks/{task_id}").get_json()["done"])

    def test_update_requires_boolean(self):
        task_id = self._create().get_json()["id"]
        res = self.client.patch(f"/tasks/{task_id}", json={"done": "yes"})
        self.assertEqual(res.status_code, 400)

    def test_update_missing_task(self):
        res = self.client.patch("/tasks/999", json={"done": True})
        self.assertEqual(res.status_code, 404)

    def test_delete_task(self):
        task_id = self._create().get_json()["id"]
        self.assertEqual(self.client.delete(f"/tasks/{task_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/tasks/{task_id}").status_code, 404)

    def test_delete_missing_task(self):
        self.assertEqual(self.client.delete("/tasks/999").status_code, 404)


if __name__ == "__main__":
    unittest.main()
