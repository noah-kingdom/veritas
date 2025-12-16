"""
VERITAS v163 - 期間未定義検出モジュール (time_limit_detector.py)
シエル殿設計に基づく実装

検出対象:
- 責任条項で期間が明示されていない
- 解除権の行使期間が未定義
- 保証・補償条項で期間が未定義

弁護士実証根拠:
- 第30条: 契約不適合責任に「2〜3年の期間限定」を提案
→ VERITASは「責任がある/ない」は見ているが「いつまでか」を評価していない
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

class ClauseCategory(Enum):
    """期間が重要な条項カテゴリ"""
    LIABILITY = "責任条項"
    TERMINATION_RIGHT = "解除権"
    WARRANTY = "保証条項"
    INDEMNITY = "補償条項"
    NON_COMPETE = "競業避止"
    CONFIDENTIALITY = "秘密保持"
    CLAIM = "請求権"
    RETENTION = "保管義務"

@dataclass
class TimeLimitResult:
    """期間検出結果"""
    clause_number: str           # 条項番号
    category: ClauseCategory     # 条項カテゴリ
    has_time_limit: bool         # 期間定義の有無
    detected_period: Optional[str]  # 検出された期間（あれば）
    trigger_text: str            # トリガーテキスト
    risk_level: str              # リスクレベル: HIGH/MEDIUM/LOW
    explanation: str             # 説明
    recommendation: str          # 推奨事項

# 期間が必要な条項パターン
TIME_SENSITIVE_PATTERNS = {
    ClauseCategory.LIABILITY: [
        (r'契約不適合(?:責任|の責任)', "契約不適合責任"),
        (r'瑕疵(?:担保)?責任', "瑕疵担保責任"),
        (r'損害賠償(?:責任|の責任|請求)', "損害賠償責任"),
        (r'(?:乙|甲).*責任を負う', "責任負担"),
    ],
    ClauseCategory.TERMINATION_RIGHT: [
        (r'解除(?:する|できる|することができる)', "解除権"),
        (r'(?:契約|本契約).*(?:解除|終了)', "契約解除"),
    ],
    ClauseCategory.WARRANTY: [
        (r'保証(?:する|期間|責任)', "保証"),
        (r'品質.*保証', "品質保証"),
    ],
    ClauseCategory.INDEMNITY: [
        (r'補償(?:する|責任|義務)', "補償"),
        (r'(?:損害|損失).*(?:填補|補填)', "損害填補"),
    ],
    ClauseCategory.NON_COMPETE: [
        (r'競業(?:避止|禁止)', "競業避止"),
        (r'同業(?:他社|者).*(?:禁止|制限)', "競業制限"),
    ],
    ClauseCategory.CONFIDENTIALITY: [
        (r'秘密(?:保持|保護|守秘)', "秘密保持"),
        (r'機密(?:保持|情報)', "機密保持"),
    ],
    ClauseCategory.CLAIM: [
        (r'請求(?:する|できる|権)', "請求権"),
        (r'追完.*請求', "追完請求"),
    ],
    ClauseCategory.RETENTION: [
        (r'(?:書類|資料|データ).*(?:保管|保存|保持)', "保管義務"),
    ],
}

# 期間表現パターン
TIME_PERIOD_PATTERNS = [
    (r'(\d+)\s*年(?:間)?', "年"),
    (r'(\d+)\s*(?:ヶ月|か月|ケ月|箇月)(?:間)?', "月"),
    (r'(\d+)\s*日(?:間)?(?:以内)?', "日"),
    (r'(\d+)\s*週間?', "週"),
    (r'引渡し?(?:の日)?から\s*(\d+)\s*(?:年|ヶ月|日)', "起算点付き"),
    (r'(?:契約|本契約)(?:終了|解除)(?:の日)?から\s*(\d+)', "終了後"),
    (r'(\d+)\s*年以内', "年以内"),
    (r'永久に|無期限|期間の定めなく', "無期限"),
]

# 例外パターン（期間不要なケース）
EXCEPTION_PATTERNS = [
    r'故意又は重(?:大な)?過失',  # 故意・重過失は期間制限しないことが一般的
    r'生命.*身体.*(?:損害|傷害)',  # 人身損害
    r'法令.*(?:定める|規定)',  # 法定期間に従う
]

def extract_time_period(text: str) -> Optional[str]:
    """テキストから期間表現を抽出"""
    for pattern, unit in TIME_PERIOD_PATTERNS:
        match = re.search(pattern, text)
        if match:
            if unit == "無期限":
                return "無期限"
            return match.group(0)
    return None

def is_exception_case(text: str) -> bool:
    """例外ケース（期間不要）かどうかを判定"""
    for pattern in EXCEPTION_PATTERNS:
        if re.search(pattern, text):
            return True
    return False

def detect_time_sensitive_clause(text: str, clause_num: str) -> List[TimeLimitResult]:
    """
    期間が重要な条項を検出し、期間定義の有無をチェック
    """
    results = []
    
    for category, patterns in TIME_SENSITIVE_PATTERNS.items():
        for pattern, label in patterns:
            if re.search(pattern, text):
                # 例外ケースをチェック
                if is_exception_case(text):
                    continue
                
                # 期間の有無をチェック
                detected_period = extract_time_period(text)
                has_time_limit = detected_period is not None
                
                # リスクレベル判定
                if not has_time_limit:
                    if category in [ClauseCategory.LIABILITY, ClauseCategory.WARRANTY]:
                        risk_level = "HIGH"
                    elif category in [ClauseCategory.CONFIDENTIALITY, ClauseCategory.NON_COMPETE]:
                        risk_level = "MEDIUM"
                    else:
                        risk_level = "LOW"
                else:
                    risk_level = "INFO"  # 情報として記録
                
                # 説明文の生成
                if has_time_limit:
                    explanation = f"期間「{detected_period}」が定義されています"
                    recommendation = "期間の妥当性を確認してください"
                else:
                    explanation = f"{label}について責任期間が明示されていません"
                    recommendation = "期間限定を設けるか、無期限とする合理性について検討を推奨します"
                
                results.append(TimeLimitResult(
                    clause_number=clause_num,
                    category=category,
                    has_time_limit=has_time_limit,
                    detected_period=detected_period,
                    trigger_text=label,
                    risk_level=risk_level,
                    explanation=explanation,
                    recommendation=recommendation
                ))
    
    return results

def analyze_article_30_pattern(text: str, clause_num: str) -> Optional[TimeLimitResult]:
    """
    弁護士指摘の第30条パターンを特別検出
    契約不適合責任で期間限定がないケース
    """
    # 契約不適合責任の検出
    if not re.search(r'契約(?:の内容に)?(?:不適合|適合しない)', text):
        return None
    
    # 追完請求や損害賠償請求の検出
    has_claim = re.search(r'(?:追完|履行|損害賠償).*(?:請求|の請求)', text)
    if not has_claim:
        return None
    
    # 期間の検出
    detected_period = extract_time_period(text)
    
    # 住宅品確法の特別規定チェック
    has_special_provision = re.search(r'住宅の品質確保.*10年', text)
    
    if not detected_period and not has_special_provision:
        return TimeLimitResult(
            clause_number=clause_num,
            category=ClauseCategory.LIABILITY,
            has_time_limit=False,
            detected_period=None,
            trigger_text="契約不適合責任",
            risk_level="HIGH",
            explanation="契約不適合責任について一般的な期間制限が設けられていません。"
                       "民法改正後の実務では2〜3年の期間限定を設けることが一般的です。",
            recommendation="「引渡しから2年（または3年）以内」等の期間限定を設けるか、"
                          "機器のメーカー保証期間と連動させることを推奨します"
        )
    
    return None

def format_output(results: List[TimeLimitResult]) -> str:
    """
    シエル殿設計の出力フォーマットに変換
    """
    # 期間未定義のみをフィルタ
    no_limit_results = [r for r in results if not r.has_time_limit]
    
    if not no_limit_results:
        return "【期間未定義】該当なし"
    
    output_lines = []
    for r in no_limit_results:
        output_lines.append(f"""
【期間未定義】{r.clause_number}
カテゴリ: {r.category.value}
リスクレベル: {r.risk_level}
本条は{r.explanation}
→ {r.recommendation}
""".strip())
    
    return "\n\n".join(output_lines)

def analyze_contract_time_limits(clauses: List[Tuple[str, str]]) -> dict:
    """
    契約書全体の期間定義を分析
    
    Args:
        clauses: (条項番号, 条項テキスト) のリスト
    
    Returns:
        分析結果の辞書
    """
    all_results = []
    
    for clause_num, clause_text in clauses:
        # 一般検出
        results = detect_time_sensitive_clause(clause_text, clause_num)
        all_results.extend(results)
        
        # 第30条パターン特別検出
        special_result = analyze_article_30_pattern(clause_text, clause_num)
        if special_result:
            all_results.append(special_result)
    
    # 重複除去（同じ条項・カテゴリの組み合わせ）
    seen = set()
    unique_results = []
    for r in all_results:
        key = (r.clause_number, r.category)
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    return {
        "total_time_sensitive": len(unique_results),
        "with_time_limit": len([r for r in unique_results if r.has_time_limit]),
        "without_time_limit": len([r for r in unique_results if not r.has_time_limit]),
        "high_risk": len([r for r in unique_results if r.risk_level == "HIGH"]),
        "medium_risk": len([r for r in unique_results if r.risk_level == "MEDIUM"]),
        "results": unique_results,
        "formatted_output": format_output(unique_results)
    }


# テスト用
if __name__ == "__main__":
    # 弁護士指摘の第30条をテスト
    test_clause = """
    第30条（契約不適合責任）
    工事目的物が契約の内容に適合しないときは、甲は、乙に対し、
    甲の指定する履行の追完の請求を行うことができるものとする。
    甲は、履行の追完の請求に代え、乙に対し、報酬の減額請求をすることができる。
    また、甲は、履行の追完の請求に代え、又はこれとともに、
    乙に対し損害賠償請求（乙の帰責事由の有無を問わない）できるものとする。
    """
    
    result = analyze_article_30_pattern(test_clause, "第30条1項")
    if result:
        print(format_output([result]))
