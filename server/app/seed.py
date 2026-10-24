"""Seed demo data: two users, one shared project, tasks in every status.

Run with:  python -m app.seed
Demo login: demo@flowdesk.dev / demo-password
"""
from .database import db, init_db, log_activity
from .security import hash_password

DEMO = ("Demo User", "demo@flowdesk.dev", "demo-password")
SECOND = ("Aoi Tanaka", "aoi@flowdesk.dev", "aoi-password")


def seed() -> None:
    init_db()
    with db() as conn:
        if conn.execute("SELECT id FROM users WHERE email = ?", (DEMO[1],)).fetchone():
            print("seed: already seeded, skipping")
            return

        def add_user(name, email, pw):
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?,?,?)",
                (name, email, hash_password(pw)),
            )
            return cur.lastrowid

        demo_id = add_user(*DEMO)
        aoi_id = add_user(*SECOND)

        cur = conn.execute(
            "INSERT INTO projects (name, description, owner_id) VALUES (?,?,?)",
            ("Webサイトリニューアル",
             "コーポレートサイトの全面リニューアル。デザイン刷新とCMS移行を含む。",
             demo_id),
        )
        project_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO project_members (project_id, user_id, role) VALUES (?,?,?)",
            [(project_id, demo_id, "owner"), (project_id, aoi_id, "member")],
        )
        log_activity(conn, project_id, demo_id, "project.created", "Webサイトリニューアル")

        tasks = [
            ("要件定義ドキュメント作成", "ヒアリング結果を要件に落とし込む", "done", "high", demo_id, None),
            ("デザインカンプ作成", "トップと下層ページの2案を作成", "review", "high", aoi_id, None),
            ("CMS選定と比較表", "候補3製品の比較表を作る", "in_progress", "medium", demo_id, None),
            ("コンテンツ棚卸し", "既存ページの棚卸しと移行可否の判定", "todo", "medium", aoi_id, None),
            ("ステージング環境構築", "本番同等構成でステージングを用意", "todo", "urgent", demo_id, None),
            ("公開前チェックリスト", "リダイレクト、OGP、計測タグの確認項目", "todo", "low", None, None),
        ]
        task_ids = []
        for title, desc, st, pri, assignee, due in tasks:
            cur = conn.execute(
                """
                INSERT INTO tasks (project_id, title, description, status, priority,
                                   assignee_id, due_date, created_by)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (project_id, title, desc, st, pri, assignee, due, demo_id),
            )
            task_ids.append(cur.lastrowid)
            log_activity(conn, project_id, demo_id, "task.created", title)

        conn.execute(
            "INSERT INTO comments (task_id, user_id, body) VALUES (?,?,?)",
            (task_ids[1], demo_id, "カンプA案をベースに進めましょう。写真の差し替えだけ別途相談します。"),
        )
        log_activity(conn, project_id, demo_id, "comment.added", tasks[1][0])
    print("seed: done (demo@flowdesk.dev / demo-password)")


if __name__ == "__main__":
    seed()
