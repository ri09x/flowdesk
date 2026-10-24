"""Aggregated dashboard statistics across all projects the user belongs to."""
from fastapi import APIRouter, Depends

from ..database import db, row_to_dict
from ..deps import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user: dict = Depends(get_current_user)):
    with db() as conn:
        my_projects = [
            r["id"]
            for r in conn.execute(
                "SELECT project_id AS id FROM project_members WHERE user_id = ?",
                (user["id"],),
            ).fetchall()
        ]
        if not my_projects:
            return {
                "project_count": 0,
                "tasks_by_status": {},
                "overdue_count": 0,
                "assigned_to_me": 0,
                "projects": [],
                "recent_activity": [],
            }
        placeholders = ",".join("?" for _ in my_projects)

        by_status = conn.execute(
            f"SELECT status, COUNT(*) AS n FROM tasks WHERE project_id IN ({placeholders}) "
            "GROUP BY status",
            my_projects,
        ).fetchall()

        overdue = conn.execute(
            f"SELECT COUNT(*) AS n FROM tasks WHERE project_id IN ({placeholders}) "
            "AND due_date IS NOT NULL AND due_date < date('now') AND status != 'done'",
            my_projects,
        ).fetchone()["n"]

        assigned = conn.execute(
            f"SELECT COUNT(*) AS n FROM tasks WHERE project_id IN ({placeholders}) "
            "AND assignee_id = ? AND status != 'done'",
            (*my_projects, user["id"]),
        ).fetchone()["n"]

        projects = conn.execute(
            f"""
            SELECT p.id, p.name,
              COUNT(t.id) AS task_count,
              SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) AS done_count
            FROM projects p
            LEFT JOIN tasks t ON t.project_id = p.id
            WHERE p.id IN ({placeholders})
            GROUP BY p.id ORDER BY p.created_at DESC
            """,
            my_projects,
        ).fetchall()

        activity = conn.execute(
            f"""
            SELECT a.*, u.name AS user_name, p.name AS project_name
            FROM activity_log a
            JOIN users u ON u.id = a.user_id
            JOIN projects p ON p.id = a.project_id
            WHERE a.project_id IN ({placeholders})
            ORDER BY a.created_at DESC, a.id DESC LIMIT 15
            """,
            my_projects,
        ).fetchall()

        return {
            "project_count": len(my_projects),
            "tasks_by_status": {r["status"]: r["n"] for r in by_status},
            "overdue_count": overdue,
            "assigned_to_me": assigned,
            "projects": [row_to_dict(r) for r in projects],
            "recent_activity": [row_to_dict(r) for r in activity],
        }
