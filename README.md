# VERITAS v144 完全版

AI契約書レビュー＆監査プラットフォーム

**Patent: 2025-159636**
「嘘なく、誇張なく、過不足なく」

## ✅ シエル殿設計 Part 4〜13 完全実装

| Part | 機能 | 状態 |
|------|------|------|
| Part 4 | リスク許容度＆フィードバック | ✅ 5段階プロファイル |
| Part 5 | 条項リライト | ✅ 50+パターン + インタラクティブ改善 |
| Part 6 | 法的根拠解決 | ✅ レポート + 弁護士メール案 |
| Part 7 | AI一貫性チェック | ✅ AI監査エンジン |
| Part 8 | NDA専用パック | ✅ 10コア項目 + A/B/C/D評価 |
| Part 9 | 業務委託専用パック | ✅ 下請法準拠チェック |
| Part 10 | Truth Engine v1 | ✅ 3層構造（事実・論理・文脈） |
| Part 11 | Dashboard | ✅ 統計ダッシュボード |
| Part 12 | TOS専用パック | ✅ 消費者契約法準拠 |
| Part 13 | AI×契約整合性 | ✅ ハルシネーション検出 |

## ✅ UI機能

- 💬 対話型チャット（VERITASと改善）
- 🔄 インタラクティブ改善ループ
- ✏️ 代替案・リライト提示
- 📁 Word/PDF/テキスト取り込み
- 🔬 担当者向け/Lawyer向けモード
- 📚 法令DB（26法律）
- ⚖️ 判例DB（10+件）
- 📧 弁護士メール案作成
- 📥 レポート出力（HTML）
- 📊 統計ダッシュボード

## ✅ コアエンジン

- v144 FALSE_OK=0保証
- 禁止パターン: 14種類
- 安全パターン: 6種類
- ゴールデン構造DB: 40構造
- 監査ログハッシュチェーン（AUD-1）
- ドメイン別閾値マップ（OKP-1）

## 🚀 デプロイ

```bash
# Streamlit Cloud
pip install -r requirements.txt
streamlit run app.py
```

## 📊 搭載DB

- 法令: 26法律（消費者契約法、下請法、労働基準法、民法、個人情報保護法等）
- 判例: 10+件（フォセコ・ジャパン事件、電通事件等）
- 代替案: 50+パターン
- 事実DB: 17エントリ（最低賃金、法定労働時間等）

## 📁 ファイル構成

```
veritas_complete/
├── app.py                 # Streamlit UI（完全版）
├── requirements.txt       # 依存関係
├── README.md              # このファイル
├── veritas.py             # CLI版
├── .streamlit/
│   └── config.toml        # テーマ設定
├── core/                  # コアエンジン
│   ├── safety_specs.py    # v144安全条件
│   ├── final_verdict.py   # 最終判定
│   ├── ng_trigger_engine.py
│   ├── smt_engine.py
│   ├── audit_logger.py
│   └── ...
├── data/                  # データ
│   └── golden_structures_v3.json
├── tools/                 # ツール
│   ├── auto_ok_suggester.py
│   ├── threshold_tuner.py
│   └── verify_audit_chain.py
├── tests/                 # テスト
│   ├── comprehensive_test.py
│   ├── real_world_test.py
│   └── stress_test.py
└── docs/                  # ドキュメント
```

---
VERITAS v144 完全版 | Patent: 2025-159636
