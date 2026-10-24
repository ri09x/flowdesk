# FlowDesk API リファレンス（要約）

ベースURL: `/api` ／ 認証: `Authorization: Bearer <JWT>`（ログイン・登録以外は必須）
対話ドキュメント: サーバー起動後に `/docs`（OpenAPI）

## 認証

| メソッド | パス | 説明 |
| --- | --- | --- |
| POST | `/auth/register` | ユーザー登録（201、トークンを返す） |
| POST | `/auth/login` | ログイン（トークンを返す） |
| GET | `/auth/me` | 現在のユーザー |

## プロジェクト

| メソッド | パス | 説明 |
| --- | --- | --- |
| POST | `/projects` | 作成（作成者が owner になる） |
| GET | `/projects` | 自分がメンバーのプロジェクト一覧（タスク数・完了数付き） |
| GET | `/projects/{id}` | 詳細（メンバー一覧付き）。非メンバーは 404 |
| PATCH | `/projects/{id}` | 名前・説明の更新（viewer 不可） |
| DELETE | `/projects/{id}` | 削除（owner のみ） |
| POST | `/projects/{id}/members` | メールアドレスでメンバー追加（role: owner/member/viewer） |

## タスクとコメント

| メソッド | パス | 説明 |
| --- | --- | --- |
| POST | `/projects/{id}/tasks` | タスク作成 |
| GET | `/projects/{id}/tasks` | 一覧。クエリ: `status_filter`, `assignee_id`, `q`（全文検索） |
| GET | `/tasks/{id}` | タスク詳細 |
| PATCH | `/tasks/{id}` | 更新。ステータス変更は活動ログに記録 |
| DELETE | `/tasks/{id}` | 削除 |
| GET | `/tasks/{id}/comments` | コメント一覧 |
| POST | `/tasks/{id}/comments` | コメント投稿 |

タスクのステータス: `todo` / `in_progress` / `review` / `done`
優先度: `low` / `medium` / `high` / `urgent`

## ダッシュボード

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/dashboard` | プロジェクト数、ステータス別タスク数、期限超過数、自分への割当数、プロジェクト別進捗、最近の活動（最大15件） |
| GET | `/health` | ヘルスチェック |
