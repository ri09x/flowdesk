from conftest import auth_header


def _project(client, token, name="Apollo"):
    res = client.post("/api/projects", json={"name": name, "description": "test"}, headers=auth_header(token))
    assert res.status_code == 201, res.text
    return res.json()


def test_project_crud_and_member_isolation(client, alice, bob):
    project = _project(client, alice["access_token"])

    mine = client.get("/api/projects", headers=auth_header(alice["access_token"])).json()
    assert any(p["id"] == project["id"] for p in mine)

    # Bob is not a member: the project must be invisible (404, not 403).
    assert client.get(f"/api/projects/{project['id']}", headers=auth_header(bob["access_token"])).status_code == 404
    bobs = client.get("/api/projects", headers=auth_header(bob["access_token"])).json()
    assert all(p["id"] != project["id"] for p in bobs)

    renamed = client.patch(
        f"/api/projects/{project['id']}", json={"name": "Apollo II"}, headers=auth_header(alice["access_token"])
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Apollo II"


def test_add_member_by_email(client, alice, bob):
    project = _project(client, alice["access_token"])
    res = client.post(
        f"/api/projects/{project['id']}/members",
        json={"email": bob["email"], "role": "member"},
        headers=auth_header(alice["access_token"]),
    )
    assert res.status_code == 201
    detail = client.get(f"/api/projects/{project['id']}", headers=auth_header(bob["access_token"]))
    assert detail.status_code == 200
    assert len(detail.json()["members"]) == 2


def test_task_lifecycle_and_filters(client, alice):
    project = _project(client, alice["access_token"])
    token = auth_header(alice["access_token"])

    t1 = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"title": "Design schema", "priority": "high"},
        headers=token,
    )
    assert t1.status_code == 201
    task = t1.json()
    assert task["status"] == "todo"

    moved = client.patch(f"/api/tasks/{task['id']}", json={"status": "in_progress"}, headers=token)
    assert moved.json()["status"] == "in_progress"

    filtered = client.get(
        f"/api/projects/{project['id']}/tasks", params={"status_filter": "in_progress"}, headers=token
    ).json()
    assert [t["id"] for t in filtered] == [task["id"]]

    searched = client.get(
        f"/api/projects/{project['id']}/tasks", params={"q": "schema"}, headers=token
    ).json()
    assert len(searched) == 1

    deleted = client.delete(f"/api/tasks/{task['id']}", headers=token)
    assert deleted.status_code == 204
    assert client.get(f"/api/tasks/{task['id']}", headers=token).status_code == 404


def test_comments_and_dashboard(client, alice):
    project = _project(client, alice["access_token"])
    token = auth_header(alice["access_token"])
    task = client.post(
        f"/api/projects/{project['id']}/tasks", json={"title": "Ship it"}, headers=token
    ).json()

    comment = client.post(
        f"/api/tasks/{task['id']}/comments", json={"body": "LGTM"}, headers=token
    )
    assert comment.status_code == 201
    assert comment.json()["author_name"] == "Alice"

    comments = client.get(f"/api/tasks/{task['id']}/comments", headers=token).json()
    assert len(comments) == 1

    dash = client.get("/api/dashboard", headers=token).json()
    assert dash["project_count"] >= 1
    assert dash["tasks_by_status"].get("todo", 0) >= 1
    assert any(a["action"] == "comment.added" for a in dash["recent_activity"])


def test_viewer_cannot_write(client, alice, bob):
    project = _project(client, alice["access_token"])
    client.post(
        f"/api/projects/{project['id']}/members",
        json={"email": bob["email"], "role": "viewer"},
        headers=auth_header(alice["access_token"]),
    )
    res = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"title": "Nope"},
        headers=auth_header(bob["access_token"]),
    )
    assert res.status_code == 403
