"""Project CRUD and membership management."""
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import db, log_activity, row_to_dict
from ..deps import get_current_user, require_project_member
from ..schemas import MemberAdd, ProjectCreate, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _project_out(conn, project_id: int) -> dict:
    row = conn.execute(
        """
        SELECT p.*,
          (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) AS task_count,
          (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status = 'done')
            AS done_count
        FROM projects p WHERE p.id = ?
        """,
        (project_id,),
    ).fetchone()
    return row_to_dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, user: dict = Depends(get_current_user)):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, description, owner_id) VALUES (?,?,?)",
            (body.name, body.description, user["id"]),
        )
        project_id = cur.lastrowid
        conn.execute(
            "INSERT INTO project_members (project_id, user_id, role) VALUES (?,?, 'owner')",
            (project_id, user["id"]),
        )
        log_activity(conn, project_id, user["id"], "project.created", body.name)
        return _project_out(conn, project_id)


@router.get("")
def list_projects(user: dict = Depends(get_current_user)):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.id FROM projects p
            JOIN project_members m ON m.project_id = p.id
            WHERE m.user_id = ?
            ORDER BY p.created_at DESC
            """,
            (user["id"],),
        ).fetchall()
        return [_project_out(conn, r["id"]) for r in rows]


@router.get("/{project_id}")
def get_project(project_id: int, user: dict = Depends(get_current_user)):
    require_project_member(project_id, user)
    with db() as conn:
        out = _project_out(conn, project_id)
        members = conn.execute(
            """
            SELECT u.id, u.name, u.email, m.role FROM project_members m
            JOIN users u ON u.id = m.user_id WHERE m.project_id = ?
            ORDER BY m.role DESC, u.name
            """,
            (project_id,),
        ).fetchall()
        out["members"] = [row_to_dict(r) for r in members]
        return out


@router.patch("/{project_id}")
def update_project(project_id: int, body: ProjectUpdate, user: dict = Depends(get_current_user)):
    require_project_member(project_id, user, write=True)
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "nothing to update")
    assignments = ", ".join(f"{k} = ?" for k in fields)
    with db() as conn:
        conn.execute(
            f"UPDATE projects SET {assignments} WHERE id = ?", (*fields.values(), project_id)
        )
        return _project_out(conn, project_id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, user: dict = Depends(get_current_user)):
    project = require_project_member(project_id, user, write=True)
    if project["my_role"] != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the owner can delete a project")
    with db() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(project_id: int, body: MemberAdd, user: dict = Depends(get_current_user)):
    require_project_member(project_id, user, write=True)
    with db() as conn:
        target = conn.execute(
            "SELECT * FROM users WHERE email = ?", (body.email.strip().lower(),)
        ).fetchone()
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no user with that email")
        try:
            conn.execute(
                "INSERT INTO project_members (project_id, user_id, role) VALUES (?,?,?)",
                (project_id, target["id"], body.role),
            )
        except Exception:
            raise HTTPException(status.HTTP_409_CONFLICT, "user is already a member")
        log_activity(conn, project_id, user["id"], "member.added", target["email"])
        return {"user_id": target["id"], "email": target["email"], "role": body.role}
