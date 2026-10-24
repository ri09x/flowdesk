"""Task CRUD with filtering, plus per-task comments."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import db, log_activity, row_to_dict
from ..deps import get_current_user, get_task_with_project, require_project_member
from ..schemas import CommentCreate, TaskCreate, TaskUpdate

router = APIRouter(prefix="/api", tags=["tasks"])


def _task_out(conn, task_id: int) -> dict:
    row = conn.execute(
        """
        SELECT t.*, u.name AS assignee_name, c.name AS creator_name,
          (SELECT COUNT(*) FROM comments cm WHERE cm.task_id = t.id) AS comment_count
        FROM tasks t
        LEFT JOIN users u ON u.id = t.assignee_id
        JOIN users c ON c.id = t.created_by
        WHERE t.id = ?
        """,
        (task_id,),
    ).fetchone()
    return row_to_dict(row)


@router.post("/projects/{project_id}/tasks", status_code=status.HTTP_201_CREATED)
def create_task(project_id: int, body: TaskCreate, user: dict = Depends(get_current_user)):
    require_project_member(project_id, user, write=True)
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO tasks (project_id, title, description, status, priority,
                               assignee_id, due_date, created_by)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (project_id, body.title, body.description, body.status, body.priority,
             body.assignee_id, body.due_date, user["id"]),
        )
        log_activity(conn, project_id, user["id"], "task.created", body.title)
        return _task_out(conn, cur.lastrowid)


@router.get("/projects/{project_id}/tasks")
def list_tasks(
    project_id: int,
    status_filter: Optional[str] = None,
    assignee_id: Optional[int] = None,
    q: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    require_project_member(project_id, user)
    sql = "SELECT t.id FROM tasks t WHERE t.project_id = ?"
    params: list = [project_id]
    if status_filter:
        sql += " AND t.status = ?"
        params.append(status_filter)
    if assignee_id is not None:
        sql += " AND t.assignee_id = ?"
        params.append(assignee_id)
    if q:
        sql += " AND (t.title LIKE ? OR t.description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY t.status, t.due_date IS NULL, t.due_date, t.created_at DESC"
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [_task_out(conn, r["id"]) for r in rows]


@router.get("/tasks/{task_id}")
def get_task(task_id: int, user: dict = Depends(get_current_user)):
    task = get_task_with_project(task_id)
    require_project_member(task["project_id"], user)
    with db() as conn:
        return _task_out(conn, task_id)


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate, user: dict = Depends(get_current_user)):
    task = get_task_with_project(task_id)
    require_project_member(task["project_id"], user, write=True)
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "nothing to update")
    assignments = ", ".join(f"{k} = ?" for k in fields)
    with db() as conn:
        conn.execute(
            f"UPDATE tasks SET {assignments}, updated_at = datetime('now') WHERE id = ?",
            (*fields.values(), task_id),
        )
        if "status" in fields and fields["status"] != task["status"]:
            log_activity(
                conn, task["project_id"], user["id"],
                "task.status_changed", f"{task['title']}: {task['status']} -> {fields['status']}",
            )
        return _task_out(conn, task_id)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, user: dict = Depends(get_current_user)):
    task = get_task_with_project(task_id)
    require_project_member(task["project_id"], user, write=True)
    with db() as conn:
        log_activity(conn, task["project_id"], user["id"], "task.deleted", task["title"])
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


@router.get("/tasks/{task_id}/comments")
def list_comments(task_id: int, user: dict = Depends(get_current_user)):
    task = get_task_with_project(task_id)
    require_project_member(task["project_id"], user)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT cm.*, u.name AS author_name FROM comments cm
            JOIN users u ON u.id = cm.user_id
            WHERE cm.task_id = ? ORDER BY cm.created_at
            """,
            (task_id,),
        ).fetchall()
        return [row_to_dict(r) for r in rows]


@router.post("/tasks/{task_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(task_id: int, body: CommentCreate, user: dict = Depends(get_current_user)):
    task = get_task_with_project(task_id)
    require_project_member(task["project_id"], user, write=True)
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO comments (task_id, user_id, body) VALUES (?,?,?)",
            (task_id, user["id"], body.body),
        )
        log_activity(conn, task["project_id"], user["id"], "comment.added", task["title"])
        row = conn.execute(
            """
            SELECT cm.*, u.name AS author_name FROM comments cm
            JOIN users u ON u.id = cm.user_id WHERE cm.id = ?
            """,
            (cur.lastrowid,),
        ).fetchone()
        return row_to_dict(row)
