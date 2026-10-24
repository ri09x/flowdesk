"""Shared FastAPI dependencies: authentication and project access control."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .database import db, row_to_dict
from .security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    try:
        user_id = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return row_to_dict(user)


def require_project_member(project_id: int, user: dict, write: bool = False) -> dict:
    """Return the project if `user` belongs to it, else raise 404.

    404 (not 403) is deliberate: non-members should not learn that the
    project exists. Viewers are rejected for write operations with 403.
    """
    with db() as conn:
        row = conn.execute(
            """
            SELECT p.*, m.role AS my_role
            FROM projects p
            JOIN project_members m ON m.project_id = p.id
            WHERE p.id = ? AND m.user_id = ?
            """,
            (project_id, user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    project = row_to_dict(row)
    if write and project["my_role"] == "viewer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "viewers cannot modify this project")
    return project


def get_task_with_project(task_id: int) -> dict:
    with db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return row_to_dict(row)
