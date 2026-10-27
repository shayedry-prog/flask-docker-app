"""Tasks API - a small Flask app backed by PostgreSQL."""

import os
import socket

from flask import Flask, jsonify, request

from . import db

APP_VERSION = os.environ.get("APP_VERSION", "dev")


def _serialize(task):
    created = task["created_at"]
    return {
        "id": task["id"],
        "title": task["title"],
        "done": bool(task["done"]),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
    }


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE_URL"] = os.environ.get(
        "DATABASE_URL", "postgresql://tasks:tasks@db:5432/tasks"
    )
    if config:
        app.config.update(config)

    db.init_db(app)
    app.teardown_appcontext(db.close_db)

    # ---------- General ----------

    @app.get("/")
    def index():
        return jsonify(
            app="tasks-api",
            version=APP_VERSION,
            container=socket.gethostname(),
            endpoints=["/health", "/tasks"],
        )

    @app.get("/health")
    def health():
        try:
            db.query("SELECT 1 AS ok", one=True)
            return jsonify(status="ok", database="up")
        except Exception as exc:  # noqa: BLE001
            app.logger.error("Health check failed: %s", exc)
            return jsonify(status="error", database="down"), 503

    # ---------- Tasks ----------

    @app.get("/tasks")
    def list_tasks():
        rows = db.query("SELECT * FROM tasks ORDER BY id")
        return jsonify([_serialize(r) for r in rows])

    @app.post("/tasks")
    def create_task():
        data = request.get_json(silent=True) or {}
        title = str(data.get("title", "")).strip()
        if not title:
            return jsonify(error="'title' is required"), 400
        if len(title) > 200:
            return jsonify(error="'title' must be 200 characters or fewer"), 400

        row = db.query(
            "INSERT INTO tasks (title) VALUES (%s) RETURNING *",
            (title,),
            one=True,
            commit=True,
        )
        return jsonify(_serialize(row)), 201

    @app.get("/tasks/<int:task_id>")
    def get_task(task_id):
        row = db.query("SELECT * FROM tasks WHERE id = %s", (task_id,), one=True)
        if row is None:
            return jsonify(error="task not found"), 404
        return jsonify(_serialize(row))

    @app.patch("/tasks/<int:task_id>")
    def update_task(task_id):
        data = request.get_json(silent=True) or {}
        if "done" not in data or not isinstance(data["done"], bool):
            return jsonify(error="'done' (true/false) is required"), 400

        row = db.query(
            "UPDATE tasks SET done = %s WHERE id = %s RETURNING *",
            (data["done"], task_id),
            one=True,
            commit=True,
        )
        if row is None:
            return jsonify(error="task not found"), 404
        return jsonify(_serialize(row))

    @app.delete("/tasks/<int:task_id>")
    def delete_task(task_id):
        row = db.query(
            "DELETE FROM tasks WHERE id = %s RETURNING id",
            (task_id,),
            one=True,
            commit=True,
        )
        if row is None:
            return jsonify(error="task not found"), 404
        return "", 204

    return app
