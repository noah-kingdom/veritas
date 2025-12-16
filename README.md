# VERITAS v167 - 完全統合版

**Patent: 2025-159636** 「嘘なく、誇張なく、過不足なく」

## 概要

VERITAS v167は、v166（Phase 4 SMT形式検証）をベースに、v163（弁護士思考分解）の新機能を統合した完全版です。

## 新機能（v167）

### 弁護士思考分解モジュール（v163より統合）

シエル殿設計に基づき、「弁護士の思考構造を分解して実装」しました。

| 機能 | 説明 | 検出対象 |
|------|------|----------|
| 曖昧性検出 | AMBIGUOUS_CLAUSE | 帰結未定義、判断主体不明、基準未定義 |
| 条項間整合性 | COHERENCE_CHECK | 効果タグ衝突、重複条項 |
| 期間未定義 | NO_TIME_LIMIT | 責任条項・解除権の期間有無 |

**実証結果**: 弁護士指摘 **6/6項目（100%）** 自動検出達成

## 既存機能（v166まで）

### Phase 1-3: 基本分析
- 禁止パターン26種、安全パターン20種
- 法令DB 16法律500+条項、判例DB 15件
- リライトパターン50+種

### Phase 4: SMT形式検証
- **SMTエンジン**: Z3/CVC5ソルバーによる形式検証
- **命題処理部**: 契約条項→一階述語論理(FOL)変換
- **形式検証部**: SAT/UNSAT判定 + 不充足コア抽出
- **PCRエンジン**: 証明付き修正案生成
- **法令公理DB**: 7件の法令公理

### Phase 5-6A: 出力・ドメイン
- 高品質Word出力
- 経営者1枚サマリー
- Domain Pack（労働/不動産/IT-SaaS）

## ファイル構成

```
veritas_v167_complete/
├── app.py                      # メインStreamlitアプリ (v167)
├── core/
│   ├── __init__.py             # コアモジュール統合
│   ├── pattern_engine.py       # 統合パターンエンジン
│   ├── edge_cases.py           # エッジケース検出（25種）
│   ├── whitelist_patterns.py   # 業界別ホワイトリスト（32種）
│   ├── context_aware.py        # 文脈依存判定
│   ├── todo_compression.py     # ToDo圧縮（90%達成）
│   └── lawyer_thinking/        # ★v163新機能
│       ├── __init__.py
│       ├── ambiguity_detector.py      # 曖昧性検出
│       ├── clause_coherence_checker.py # 条項間整合性
│       └── time_limit_detector.py     # 期間未定義検出
├── domains/
│   ├── labor_pack.py           # 雇用/出向/偽装請負（24種）
│   ├── realestate_pack.py      # 賃貸借/売買（24種）
│   └── it_saas_pack.py         # 利用規約/SLA（26種）
├── output/
│   ├── professional_report_docx.js  # Word出力
│   └── executive_summary.js         # 経営者サマリー
├── tests/
│   ├── test_case_law.py        # 判例テスト（66件）
│   ├── test_industry_terms.py  # 業界約款テスト（100件）
│   └── phase159_accuracy_test.py
└── requirements.txt
```

## 使用方法

### 起動
```bash
pip install -r requirements.txt
streamlit run app.py
```

### API使用（Python）
```python
from core import quick_analyze, compress_todos
from core.lawyer_thinking import analyze_ambiguity, analyze_contract_coherence

# 基本分析
result = quick_analyze(contract_text)

# 弁護士思考分析
ambiguity_results = analyze_ambiguity(clause_text, "第15条2項")
coherence_result = analyze_contract_coherence(contract_text)
```

## 品質指標

| 指標 | 数値 |
|------|------|
| FALSE_OK（見逃し） | **0件** |
| 弁護士指摘カバー率 | **100%** (6/6) |
| 判例テスト | 66件合格 |
| 業界約款テスト | 100件合格 |
| 総パターン | 300+ |

## VERITASの位置づけ

✅ **VERITASがやること**
- 論点の可視化
- 見逃し防止
- 思考補助

❌ **VERITASがやらないこと**
- 修正文案の確定提示
- 法的妥当性の断定
- 削除・存置の最終判断

## 技術仕様

- Python 3.10+
- Streamlit 1.28+
- Z3 Solver（オプション）
- spaCy（日本語NLP）

## ライセンス

Proprietary - Noah王国 / VERITAS Project

---

*「嘘なく、誇張なく、過不足なく」*
