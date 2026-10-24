# FlowDesk

チーム向けプロジェクト管理アプリケーション（フルスタック）。
プロジェクト、カンバンタスク、コメント、メンバー権限、活動ログ、ダッシュボード集計を備えた、業務アプリ相当の構成で実装しています。

## 機能

- **認証**: ユーザー登録／ログイン（JWT、パスワードは PBKDF2 ハッシュで保存）
- **プロジェクト**: 作成・編集・削除、メールアドレスでのメンバー招待、ロール権限（owner / member / viewer）
- **タスク**: カンバン（未着手／進行中／レビュー／完了）、ドラッグ＆ドロップでのステータス変更、優先度・担当者・期限、検索と絞り込み
- **コメント**: タスクごとのディスカッション
- **ダッシュボード**: ステータス別集計、期限超過、自分への割当、プロジェクト進捗、活動フィード
- **アクセス制御**: 非メンバーのプロジェクトは存在自体を見せない（404）設計

## 技術構成

| 層 | 技術 |
| --- | --- |
| バックエンド | Python 3.12 / FastAPI / SQLite / PyJWT |
| フロントエンド | HTML / CSS / JavaScript（ES Modules、ビルドなし） |
| テスト | pytest + FastAPI TestClient（認証・権限・タスク生命周期・集計） |
| CI | GitHub Actions（pytest + JS 構文チェック） |
| 実行 | Docker Compose 対応 |

アーキテクチャ図と設計判断は [docs/architecture.md](docs/architecture.md)、API の要約は [docs/api.md](docs/api.md) を参照してください。

## ローカルで動かす

### Docker Compose

```bash
docker compose up --build
# http://localhost:8000
```

### 直接実行

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed        # デモデータを投入
uvicorn app.main:app --reload --port 8000
# http://localhost:8000  （APIドキュメントは /docs）
```

デモアカウント: `demo@flowdesk.dev` / `demo-password`

## テスト

```bash
cd server
python -m pytest -q
```

## ディレクトリ構成

```
flowdesk/
├── server/            # FastAPI アプリケーション
│   ├── app/
│   │   ├── main.py        # エントリポイント（API + 静的配信）
│   │   ├── database.py    # スキーマと接続管理
│   │   ├── security.py    # パスワードハッシュ / JWT
│   │   ├── deps.py        # 認証・権限の共通依存
│   │   ├── schemas.py     # リクエスト/レスポンス定義
│   │   ├── seed.py        # デモデータ
│   │   └── routers/       # auth / projects / tasks / dashboard
│   ├── tests/             # pytest
│   ├── requirements.txt
│   └── Dockerfile
├── web/               # SPA（APIクライアント層を分離）
│   ├── index.html
│   ├── css/app.css
│   └── js/{api.js, app.js}
├── docs/              # architecture.md / api.md
└── docker-compose.yml
```
