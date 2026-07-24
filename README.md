# 大誠株式会社 不動産週報

東京不动產市場の最新動向を毎週配信するレポートレポジトリです。

## 📌 このレポジトリについて

- **目的**：大誠abore様が每周客户に配信する不動産週報の公開レポジトリ
- **公開先**：EdgeOne Pages（GitHub Pages的なもの）
- **更新周期**：毎週火曜日（JST 09:00）

## 📂 ディレクトリ構成

```
taisei-weekly-reports/
├── reports/                  # 毎週のレポート（自動生成）
│   ├── 2026-07-13/         # 各週のフォルダ
│   │   └── report.html
│   └── ...
├── generate_weekly.py       # 週次レポート生成スクリプト
├── report_template.html     # レポートHTMLテンプレート
└── README.md
```

## 🚀 使い方

### 每周のレポート生成

```bash
python generate_weekly.py
```

このスクリプトが以下を実行します：
1. 今週のレポートHTMLを生成
2. `reports/YYYY-MM-DD/report.html` に保存
3. GitHubに自動commit & push
4. EdgeOne Pagesが自動检测&发布

### 手動でpushする場合

```bash
cd taisei-weekly-reports
git add reports/
git commit -m "Add weekly report: YYYY-MM-DD"
git push origin main
```

## 🔧 初回セットアップ

1. GitHubにレポジトリを作成（このスクリプトが自動実行）
2. EdgeOne Pagesで「从GitHub导入」，対象レポジトリを選択
3. ブランチ：`main`，构建命令：空，输出目录：`/`
4. 以降は `python generate_weekly.py` のみで更新可能

## 📡 アクセス

EdgeOne Pagesの公开URLをEdgeOneコンソールで確認してください。
