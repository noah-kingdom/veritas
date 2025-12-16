"""
VERITAS v163 - 曖昧性検出モジュール (ambiguity_detector.py)
シエル殿設計に基づく実装

検出対象:
1. 条件語を含むが帰結が未定義
2. 判断主体が不明
3. 判断基準が数値・手続で定義されていない

弁護士実証根拠:
- 第15条2項: 工事責任者不在時の対応不明
- 第25条8項:「乙の自主検査でよい」の解釈曖昧
- 第28条③:「検査」＝何を意味するか不明
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

class AmbiguityType(Enum):
    """曖昧性の種類"""
    UNDEFINED_CONSEQUENCE = "帰結未定義"      # 条件語あるが帰結なし
    UNCLEAR_SUBJECT = "判断主体不明"          # 誰が判断するか不明
    NO_OBJECTIVE_CRITERIA = "基準未定義"      # 数値・手続が定義されていない
    INTERPRETATION_VARIANCE = "解釈幅大"      # 解釈に幅が生じる可能性

@dataclass
class AmbiguityResult:
    """曖昧性検出結果"""
    clause_number: str              # 条項番号（例: "第15条2項"）
    ambiguity_type: AmbiguityType   # 曖昧性の種類
    trigger_text: str               # トリガーとなったテキスト
    explanation: str                # 説明
    recommendation: str             # 推奨アクション
    severity: str                   # 重要度: HIGH/MEDIUM/LOW

# 条件語パターン（帰結未定義の検出用）
CONDITIONAL_PATTERNS = [
    r'の場合(?!は|には|において)',           # 「〜の場合」で帰結がない
    r'ときは(?!、|。)',                      # 「〜ときは」で続きがない
    r'必要に応じて(?!、|[^。]{5,})',         # 「必要に応じて」で具体性なし
    r'(?:甲|乙)が(?:必要|適当)と(?:認めた|判断した)(?:場合|とき)',  # 主観的判断
]

# 判断主体不明パターン
UNCLEAR_SUBJECT_PATTERNS = [
    r'(?:検査|確認|承認|判断|決定)(?:する|を行う|される)',  # 主語なしの動作
    r'(?:定める|指定する|指示する)(?:ところ|もの)による',    # 誰が定めるか不明
    r'工事責任者等(?:の指示|が定め)',                       # 「等」で範囲不明
]

# 客観基準なしパターン
NO_CRITERIA_PATTERNS = [
    (r'適切に', '「適切」の基準が未定義'),
    (r'速やかに', '「速やか」の期限が未定義'),
    (r'合理的(?:な|に)', '「合理的」の基準が未定義'),
    (r'相当(?:の|な|期間)', '「相当」の基準が未定義'),
    (r'必要な(?:措置|対応|手続)', '「必要」の範囲が未定義'),
    (r'適当(?:な|と認める)', '「適当」の基準が未定義'),
    (r'遅滞なく', '具体的期限が未定義'),
    (r'直ちに', '具体的期限が未定義'),
    (r'正当な理由', '「正当な理由」の定義が未定義'),
]

# 条項番号抽出パターン
CLAUSE_NUMBER_PATTERN = r'第(\d+)条(?:[（(]([^）)]+)[）)])?(?:の(\d+))?(?:第?(\d+)項)?'

def extract_clause_number(text: str) -> Optional[str]:
    """テキストから条項番号を抽出"""
    match = re.search(CLAUSE_NUMBER_PATTERN, text)
    if match:
        article = match.group(1)
        title = match.group(2) or ""
        sub = match.group(3) or ""
        paragraph = match.group(4) or ""
        
        result = f"第{article}条"
        if title:
            result += f"（{title}）"
        if sub:
            result += f"の{sub}"
        if paragraph:
            result += f"第{paragraph}項"
        return result
    return None

def detect_undefined_consequence(clause_text: str, clause_num: str) -> List[AmbiguityResult]:
    """条件語はあるが帰結が未定義のケースを検出"""
    results = []
    
    for pattern in CONDITIONAL_PATTERNS:
        matches = re.finditer(pattern, clause_text)
        for match in matches:
            # 前後の文脈を取得
            start = max(0, match.start() - 30)
            end = min(len(clause_text), match.end() + 50)
            context = clause_text[start:end]
            
            results.append(AmbiguityResult(
                clause_number=clause_num,
                ambiguity_type=AmbiguityType.UNDEFINED_CONSEQUENCE,
                trigger_text=match.group(),
                explanation=f"「{match.group()}」に対する帰結・対応が明示されていません",
                recommendation="条件成立時の具体的な対応・帰結を追記することを推奨します",
                severity="MEDIUM"
            ))
    
    return results

def detect_unclear_subject(clause_text: str, clause_num: str) -> List[AmbiguityResult]:
    """判断主体が不明なケースを検出"""
    results = []
    
    for pattern in UNCLEAR_SUBJECT_PATTERNS:
        matches = re.finditer(pattern, clause_text)
        for match in matches:
            # 主語の有無をチェック（甲/乙/第三者が近くにあるか）
            start = max(0, match.start() - 20)
            preceding = clause_text[start:match.start()]
            
            if not re.search(r'[甲乙](?:は|が|の)', preceding):
                results.append(AmbiguityResult(
                    clause_number=clause_num,
                    ambiguity_type=AmbiguityType.UNCLEAR_SUBJECT,
                    trigger_text=match.group(),
                    explanation=f"「{match.group()}」の判断主体（甲/乙/第三者）が明確でありません",
                    recommendation="判断主体を明示するか、主体不在時の対応を追記することを推奨します",
                    severity="HIGH"
                ))
    
    return results

def detect_no_objective_criteria(clause_text: str, clause_num: str) -> List[AmbiguityResult]:
    """客観的基準がないケースを検出"""
    results = []
    
    for pattern, description in NO_CRITERIA_PATTERNS:
        matches = re.finditer(pattern, clause_text)
        for match in matches:
            results.append(AmbiguityResult(
                clause_number=clause_num,
                ambiguity_type=AmbiguityType.NO_OBJECTIVE_CRITERIA,
                trigger_text=match.group(),
                explanation=description,
                recommendation="数値・期限・手続等の客観的基準を定めることを推奨します",
                severity="MEDIUM"
            ))
    
    return results

def detect_special_cases(clause_text: str, clause_num: str) -> List[AmbiguityResult]:
    """弁護士指摘に基づく特殊ケース検出"""
    results = []
    
    # 第26条パターン: 維持管理協力義務で責任範囲が未限定
    if re.search(r'維持管理.*協力', clause_text) or re.search(r'協力しなければならない', clause_text):
        # 責任限定条項があるかチェック
        has_limitation = re.search(r'(?:責に帰すべき事由|帰責事由).*(?:除き|場合を除)', clause_text)
        if not has_limitation:
            results.append(AmbiguityResult(
                clause_number=clause_num,
                ambiguity_type=AmbiguityType.NO_OBJECTIVE_CRITERIA,
                trigger_text="協力義務",
                explanation="協力義務の範囲・責任限定が明示されていません。"
                           "帰責性がある場合のみ責任を負う旨の限定がないと、"
                           "過大な責任を負う可能性があります",
                recommendation="「ただし、乙の責に帰すべき事由による場合を除き、"
                              "その責任を負わない」等の追記を推奨します",
                severity="MEDIUM"
            ))
    
    # 第15条2項パターン: 工事責任者等がいない場合
    if re.search(r'工事責任者等', clause_text):
        if not re.search(r'(?:定めない|いない|不在)(?:場合|とき)', clause_text):
            results.append(AmbiguityResult(
                clause_number=clause_num,
                ambiguity_type=AmbiguityType.UNDEFINED_CONSEQUENCE,
                trigger_text="工事責任者等",
                explanation="工事責任者等が定められていない場合の対応が明示されていません",
                recommendation="「工事責任者等を定めない場合においては、甲の指示による」等の追記を推奨します",
                severity="HIGH"
            ))
    
    # 第25条8項パターン: 自主検査の解釈
    if re.search(r'自主検査', clause_text):
        if re.search(r'代えて|に代わり', clause_text):
            results.append(AmbiguityResult(
                clause_number=clause_num,
                ambiguity_type=AmbiguityType.INTERPRETATION_VARIANCE,
                trigger_text="自主検査に代えて",
                explanation="「自主検査でよい」の解釈に幅が生じる可能性があります",
                recommendation="省略可能な検査手続と必須の検査手続を明確化することを推奨します",
                severity="MEDIUM"
            ))
    
    # 第28条パターン: 「検査」の意味
    if re.search(r'(?:甲の)?検査(?:又は|または)', clause_text):
        if not re.search(r'検査に合格', clause_text):
            results.append(AmbiguityResult(
                clause_number=clause_num,
                ambiguity_type=AmbiguityType.INTERPRETATION_VARIANCE,
                trigger_text="検査",
                explanation="「検査」が「検査実施」と「検査合格」のどちらを意味するか不明確です",
                recommendation="「検査に合格した場合」等、条件を明確化することを推奨します",
                severity="MEDIUM"
            ))
    
    return results

def analyze_clause(clause_text: str, clause_num: str = None) -> List[AmbiguityResult]:
    """
    単一条項の曖昧性を分析
    
    Args:
        clause_text: 条項のテキスト
        clause_num: 条項番号（Noneの場合はテキストから抽出を試みる）
    
    Returns:
        検出された曖昧性のリスト
    """
    if clause_num is None:
        clause_num = extract_clause_number(clause_text) or "（条項番号不明）"
    
    results = []
    results.extend(detect_undefined_consequence(clause_text, clause_num))
    results.extend(detect_unclear_subject(clause_text, clause_num))
    results.extend(detect_no_objective_criteria(clause_text, clause_num))
    results.extend(detect_special_cases(clause_text, clause_num))
    
    return results

def format_output(results: List[AmbiguityResult]) -> str:
    """
    シエル殿設計の出力フォーマットに変換
    """
    if not results:
        return "【曖昧性検出】該当なし"
    
    output_lines = []
    for r in results:
        output_lines.append(f"""
【曖昧性検出】{r.clause_number}
種別: {r.ambiguity_type.value}
重要度: {r.severity}
本条は「{r.trigger_text}」について、{r.explanation}
契約解釈に幅が生じる可能性があります。
→ {r.recommendation}
""".strip())
    
    return "\n\n".join(output_lines)

def analyze_contract(clauses: List[Tuple[str, str]]) -> dict:
    """
    契約書全体の曖昧性を分析
    
    Args:
        clauses: (条項番号, 条項テキスト) のリスト
    
    Returns:
        分析結果の辞書
    """
    all_results = []
    for clause_num, clause_text in clauses:
        results = analyze_clause(clause_text, clause_num)
        all_results.extend(results)
    
    return {
        "total_ambiguities": len(all_results),
        "by_type": {
            t.value: len([r for r in all_results if r.ambiguity_type == t])
            for t in AmbiguityType
        },
        "by_severity": {
            s: len([r for r in all_results if r.severity == s])
            for s in ["HIGH", "MEDIUM", "LOW"]
        },
        "results": all_results,
        "formatted_output": format_output(all_results)
    }


# テスト用
if __name__ == "__main__":
    # 弁護士指摘の第15条2項をテスト
    test_clause = """
    第15条（使用材料の品質）
    2. 設計図書及び甲の作成した指示書において使用すべき工事材料等が
       指定されていないときは、工事責任者等の指示による。
    """
    
    results = analyze_clause(test_clause, "第15条2項")
    print(format_output(results))
