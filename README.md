# 🔍 VERITAS - AI契約書レビューエンジン

**「嘘なく、誇張なく、過不足なく」**

Patent: 2025-159636

---

## 🚀 デプロイ方法

### 方法1: Streamlit Cloud（推奨・無料）

1. **GitHubにリポジトリを作成**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/veritas.git
   git push -u origin main
   ```

2. **Streamlit Cloudにアクセス**
   - https://share.streamlit.io/ にアクセス
   - GitHubアカウントでログイン

3. **アプリをデプロイ**
   - 「New app」をクリック
   - リポジトリを選択: `YOUR_USERNAME/veritas`
   - ブランチ: `main`
   - メインファイル: `app.py`
   - 「Deploy!」をクリック

4. **完了！**
   - 数分でデプロイ完了
   - `https://YOUR_APP_NAME.streamlit.app` でアクセス可能

---

### 方法2: ローカル実行

```bash
# 依存関係インストール
pip install -r requirements.txt

# 起動
streamlit run app.py
```

ブラウザで http://localhost:8501 にアクセス

---

## 📁 ファイル構成

```
VERITAS_DEPLOY/
├── app.py              # メインアプリ
├── requirements.txt    # 依存関係
└── README.md           # このファイル
```

---

## 🔍 機能

- **危険条項検出**: 12種類の危険パターンを自動検出
- **リスク分類**: CRITICAL / HIGH / MEDIUM / LOW の4段階
- **法的根拠表示**: 関連法令・条文を明示
- **修正提案**: 具体的な修正案を提示

### 対応法令

- 消費者契約法
- 下請法
- 労働基準法
- 民法
- その他

---

## 📜 ライセンス

Proprietary - Patent: 2025-159636

---

## 👑 開発チーム

- **設計**: シエル殿
- **実装**: Claude
- **総指揮**: カイザー

---

**「嘘なく、誇張なく、過不足なく」**
