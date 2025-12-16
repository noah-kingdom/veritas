"""
VERITAS v163 - 条項間整合性チェックモジュール (clause_coherence_checker.py)
シエル殿設計に基づく実装

検出対象:
- 効果タグが同一 AND 発動条件が類似 AND 条項番号が異なる → 重複候補

弁護士実証根拠:
- 第35条⑤ と 第35条⑩ → 内容一部重複（社会的信用も含むため残す判断）

VERITASの役割:
- 重複を検出 → 人間が「残す/削る」を判断
- 削除判断はしない（判断は人間）
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum
from collections import defaultdict

class EffectTag(Enum):
    """条項の効果タグ"""
    TERMINATION = "解除"
    DAMAGES = "損害賠償"
    CREDIT_LOSS = "信用毀損"
    CONTRACT_END = "契約終了"
    OBLIGATION = "義務"
    RIGHT = "権利"
    RESTRICTION = "制限"
    EXCEPTION = "例外"
    NOTIFICATION = "通知"
    APPROVAL = "承認"
    INSPECTION = "検査"
    DELIVERY = "引渡"
    PAYMENT = "支払"
    LIABILITY = "責任"
    INDEMNITY = "補償"
    CONFIDENTIALITY = "秘密保持"
    FORCE_MAJEURE = "不可抗力"

@dataclass
class ClauseInfo:
    """条項情報"""
    clause_number: str           # 条項番号
    text: str                    # 条項テキスト
    effect_tags: Set[EffectTag] = field(default_factory=set)
    trigger_conditions: List[str] = field(default_factory=list)
    
@dataclass
class CoherenceResult:
    """整合性チェック結果"""
    clause_a: str               # 条項A
    clause_b: str               # 条項B
    overlap_type: str           # 重複タイプ
    shared_effects: Set[str]    # 共通する効果
    similarity_score: float     # 類似度スコア (0-1)
    explanation: str            # 説明
    recommendation: str         # 推奨事項

# 効果タグ検出パターン
EFFECT_PATTERNS = {
    EffectTag.TERMINATION: [
        r'解除(?:する|できる|することができる)',
        r'(?:直ちに|即時に).*解除',
        r'契約.*(?:解除|終了)',
    ],
    EffectTag.DAMAGES: [
        r'損害(?:賠償|を賠償|の賠償)',
        r'賠償(?:請求|を請求|の請求)',
        r'損害等.*負担',
    ],
    EffectTag.CREDIT_LOSS: [
        r'信用.*(?:失|毀損|低下)',
        r'(?:社会的|経済的).*信用',
        r'信頼.*失',
    ],
    EffectTag.CONTRACT_END: [
        r'契約.*終了',
        r'(?:本契約|個別契約).*(?:解除|終了|消滅)',
    ],
    EffectTag.OBLIGATION: [
        r'(?:しなければならない|義務|責任を負う)',
        r'(?:〜ものとする|〜こととする)',
    ],
    EffectTag.NOTIFICATION: [
        r'通知(?:する|しなければ|を行う)',
        r'報告(?:する|しなければ)',
    ],
    EffectTag.INSPECTION: [
        r'検査(?:する|を行う|を受ける)',
        r'確認(?:する|を行う)',
    ],
    EffectTag.PAYMENT: [
        r'支払(?:う|い|われる)',
        r'(?:代金|報酬|対価).*(?:支払|払う)',
    ],
    EffectTag.LIABILITY: [
        r'責任.*(?:負う|を負担|免れ)',
        r'(?:契約不適合|瑕疵).*責任',
    ],
}

# 発動条件パターン
TRIGGER_PATTERNS = [
    (r'(?:資産|信用|事業).*(?:重大な変更|変動)', "経済的変動"),
    (r'(?:仮差押|差押|仮処分|競売)', "法的手続"),
    (r'(?:破産|民事再生|会社更生|特別清算)', "倒産手続"),
    (r'(?:公租公課|滞納処分)', "租税滞納"),
    (r'(?:取引停止|不渡り|支払停止)', "金融事故"),
    (r'(?:許可|免許).*(?:失効|取消)', "許認可喪失"),
    (r'(?:解散|合併|分割|事業譲渡)', "組織再編"),
    (r'信用.*(?:失|毀損)', "信用毀損"),
    (r'(?:違反|不履行)', "契約違反"),
    (r'(?:遅延|遅滞)', "履行遅延"),
]

def extract_effect_tags(text: str) -> Set[EffectTag]:
    """テキストから効果タグを抽出"""
    tags = set()
    for tag, patterns in EFFECT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                tags.add(tag)
                break
    return tags

def extract_trigger_conditions(text: str) -> List[str]:
    """テキストから発動条件を抽出"""
    conditions = []
    for pattern, label in TRIGGER_PATTERNS:
        if re.search(pattern, text):
            conditions.append(label)
    return conditions

def calculate_similarity(clause_a: ClauseInfo, clause_b: ClauseInfo) -> float:
    """
    2つの条項の類似度を計算
    効果タグとトリガー条件の重複度合いで算出
    """
    # 効果タグの類似度
    if clause_a.effect_tags and clause_b.effect_tags:
        effect_overlap = len(clause_a.effect_tags & clause_b.effect_tags)
        effect_total = len(clause_a.effect_tags | clause_b.effect_tags)
        effect_sim = effect_overlap / effect_total if effect_total > 0 else 0
    else:
        effect_sim = 0
    
    # トリガー条件の類似度
    trigger_a = set(clause_a.trigger_conditions)
    trigger_b = set(clause_b.trigger_conditions)
    if trigger_a and trigger_b:
        trigger_overlap = len(trigger_a & trigger_b)
        trigger_total = len(trigger_a | trigger_b)
        trigger_sim = trigger_overlap / trigger_total if trigger_total > 0 else 0
    else:
        trigger_sim = 0
    
    # 重み付き平均（効果タグを重視）
    return 0.6 * effect_sim + 0.4 * trigger_sim

def analyze_clause_pair(clause_a: ClauseInfo, clause_b: ClauseInfo) -> Optional[CoherenceResult]:
    """
    2つの条項の整合性をチェック
    """
    # 同じ条項番号は除外
    if clause_a.clause_number == clause_b.clause_number:
        return None
    
    # 効果タグの共通部分
    shared_effects = clause_a.effect_tags & clause_b.effect_tags
    if not shared_effects:
        return None
    
    # 類似度計算
    similarity = calculate_similarity(clause_a, clause_b)
    
    # 閾値以上なら重複候補
    if similarity < 0.3:
        return None
    
    # 重複タイプの判定
    if similarity >= 0.7:
        overlap_type = "高重複"
    elif similarity >= 0.5:
        overlap_type = "中重複"
    else:
        overlap_type = "低重複（関連性あり）"
    
    return CoherenceResult(
        clause_a=clause_a.clause_number,
        clause_b=clause_b.clause_number,
        overlap_type=overlap_type,
        shared_effects={e.value for e in shared_effects},
        similarity_score=similarity,
        explanation=f"両条項は「{', '.join(e.value for e in shared_effects)}」の効果を共有しています",
        recommendation="目的が異なる場合は併存可能ですが、整理・明確化の余地があります"
    )

def parse_contract_clauses(contract_text: str) -> List[ClauseInfo]:
    """
    契約書テキストから条項を解析
    """
    clauses = []
    
    # 条項パターンで分割
    clause_pattern = r'(第\d+条[（(][^）)]+[）)]?(?:.*?)(?=第\d+条|$))'
    
    # より単純なアプローチ：行ごとに処理
    lines = contract_text.split('\n')
    current_clause_num = None
    current_clause_text = []
    
    for line in lines:
        # 新しい条項の開始を検出
        match = re.match(r'(第\d+条[（(][^）)]+[）)]?)', line)
        if match:
            # 前の条項を保存
            if current_clause_num and current_clause_text:
                text = '\n'.join(current_clause_text)
                clauses.append(ClauseInfo(
                    clause_number=current_clause_num,
                    text=text,
                    effect_tags=extract_effect_tags(text),
                    trigger_conditions=extract_trigger_conditions(text)
                ))
            
            current_clause_num = match.group(1)
            current_clause_text = [line]
        elif current_clause_num:
            current_clause_text.append(line)
    
    # 最後の条項を保存
    if current_clause_num and current_clause_text:
        text = '\n'.join(current_clause_text)
        clauses.append(ClauseInfo(
            clause_number=current_clause_num,
            text=text,
            effect_tags=extract_effect_tags(text),
            trigger_conditions=extract_trigger_conditions(text)
        ))
    
    return clauses

def check_coherence(clauses: List[ClauseInfo]) -> List[CoherenceResult]:
    """
    契約書全体の条項間整合性をチェック
    """
    results = []
    
    # 全ペアをチェック
    for i, clause_a in enumerate(clauses):
        for clause_b in clauses[i+1:]:
            result = analyze_clause_pair(clause_a, clause_b)
            if result:
                results.append(result)
    
    # 類似度順にソート
    results.sort(key=lambda x: x.similarity_score, reverse=True)
    
    return results

def format_output(results: List[CoherenceResult]) -> str:
    """
    シエル殿設計の出力フォーマットに変換
    """
    if not results:
        return "【条項整合性チェック】重複候補なし"
    
    output_lines = []
    for r in results:
        output_lines.append(f"""
【条項整合性チェック】{r.clause_a} ↔ {r.clause_b}
重複タイプ: {r.overlap_type}（類似度: {r.similarity_score:.1%}）
共通効果: {', '.join(r.shared_effects)}
{r.explanation}
→ {r.recommendation}
""".strip())
    
    return "\n\n".join(output_lines)

def analyze_contract_coherence(contract_text: str) -> dict:
    """
    契約書全体の整合性を分析
    
    Args:
        contract_text: 契約書全文
    
    Returns:
        分析結果の辞書
    """
    clauses = parse_contract_clauses(contract_text)
    results = check_coherence(clauses)
    
    return {
        "total_clauses": len(clauses),
        "overlap_candidates": len(results),
        "high_overlap": len([r for r in results if r.similarity_score >= 0.7]),
        "medium_overlap": len([r for r in results if 0.5 <= r.similarity_score < 0.7]),
        "low_overlap": len([r for r in results if r.similarity_score < 0.5]),
        "results": results,
        "formatted_output": format_output(results)
    }


# 弁護士指摘の第35条をテスト
if __name__ == "__main__":
    test_text = """
第35条（甲の即時解除）
甲は、乙が次の各号のいずれかに該当するときは、何らの通知、催告も行うことなく
直ちに本契約及び個別契約の全部又は一部を解除することができる。
⑤ 資産、信用又は事業に重大な変更を生じ、契約の履行が困難と認められるとき
（仮差押、差押、仮処分若しくは競売の申請又は破産、民事再生、会社更生若しくは
特別清算の申立てがあったとき又は公租公課の滞納処分を受けたとき若しくは
清算に入ったときを含む。）。
⑩ その他乙に信用を失う事由が生じたとき。
"""
    
    # 手動でClauseInfoを作成してテスト
    clause_5 = ClauseInfo(
        clause_number="第35条⑤",
        text="資産、信用又は事業に重大な変更を生じ、契約の履行が困難と認められるとき",
        effect_tags={EffectTag.TERMINATION, EffectTag.CREDIT_LOSS},
        trigger_conditions=["経済的変動", "法的手続", "倒産手続", "租税滞納"]
    )
    
    clause_10 = ClauseInfo(
        clause_number="第35条⑩",
        text="その他乙に信用を失う事由が生じたとき",
        effect_tags={EffectTag.TERMINATION, EffectTag.CREDIT_LOSS},
        trigger_conditions=["信用毀損"]
    )
    
    result = analyze_clause_pair(clause_5, clause_10)
    if result:
        print(format_output([result]))
