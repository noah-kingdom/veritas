"""
VERITAS v159 - Context-Aware Judgment Engine
文脈依存判定モジュール

「微妙なライン」の条項を文脈から判定
- 単独では判定困難な条項
- 緩和条件・強化条件による判定変化
- 前後の文脈を考慮した総合判定

設計原則:
- FALSE_OK=0 の死守（迷ったらREVIEW）
- 文脈による判定精度向上
- 人間の法務担当者の判断プロセスを模倣
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ContextVerdict(Enum):
    """文脈依存判定結果"""
    NG_CRITICAL = "NG_CRITICAL"
    NG = "NG"
    REVIEW_HIGH = "REVIEW_HIGH"
    REVIEW_MED = "REVIEW_MED"
    OK_CONDITIONAL = "OK_CONDITIONAL"
    OK = "OK"
    UNDETERMINED = "UNDETERMINED"  # 文脈不足で判定不能


@dataclass
class ContextModifier:
    """判定を変化させる文脈条件"""
    pattern: str
    effect: str  # "mitigate" (緩和) or "aggravate" (強化)
    verdict_change: ContextVerdict
    explanation: str


@dataclass
class ContextAwareResult:
    """文脈依存判定結果"""
    base_verdict: ContextVerdict      # 単独での判定
    final_verdict: ContextVerdict     # 文脈考慮後の判定
    trigger_name: str
    matched_base_text: str
    modifiers_found: List[str]        # 検出された文脈条件
    context_explanation: str
    check_points: List[str]
    legal_basis: str


# =============================================================================
# 文脈依存トリガー定義
# =============================================================================

CONTEXT_TRIGGERS = {
    # =========================================================================
    # 免責条項系
    # =========================================================================
    "liability_waiver": {
        "base_pattern": r"(責任を負わない|責任を負いません|免責とする|免責とします)",
        "base_verdict": ContextVerdict.REVIEW_HIGH,
        "base_explanation": "免責条項。単独では範囲不明のため要確認",
        "check_points": [
            "免責の範囲を確認",
            "故意・重過失の除外有無",
            "消費者契約法8条との整合性"
        ],
        "legal_basis": "消費者契約法8条",
        
        # 緩和条件（これがあればOKに近づく）
        "mitigating_modifiers": [
            {
                "pattern": r"(故意|重過失).{0,10}(除き?|を除く|の場合を除き|による.{0,5}除く)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "故意・重過失を除外しており、法的に有効な免責範囲"
            },
            {
                "pattern": r"(軽過失|通常の過失).{0,10}(に限り|についてのみ|の場合のみ)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "軽過失のみの免責であり、合理的な範囲"
            },
            {
                "pattern": r"(○|〇|\d+).{0,5}(万円|円).{0,10}(を上限|を限度|まで)",
                "verdict_change": ContextVerdict.REVIEW_MED,
                "explanation": "賠償上限の設定あり。上限額の妥当性を確認"
            },
        ],
        
        # 強化条件（これがあればNGに近づく）
        "aggravating_modifiers": [
            {
                "pattern": r"(一切|いかなる|すべて|全て|あらゆる)",
                "verdict_change": ContextVerdict.NG_CRITICAL,
                "explanation": "全面免責条項。消費者契約法8条で無効"
            },
            {
                "pattern": r"(理由の如何|原因の如何|事由の如何).{0,10}(を問わず|にかかわらず|に関わらず)",
                "verdict_change": ContextVerdict.NG,
                "explanation": "原因を問わない免責。実質的な全面免責"
            },
            {
                "pattern": r"(故意|重過失).{0,10}(含め|であっても|の場合も)",
                "verdict_change": ContextVerdict.NG_CRITICAL,
                "explanation": "故意・重過失も含めた免責。明確に無効"
            },
        ],
    },
    
    # =========================================================================
    # 損害賠償条項系
    # =========================================================================
    "damages_clause": {
        "base_pattern": r"(損害賠償|賠償|補償).{0,10}(請求|求める|支払う)",
        "base_verdict": ContextVerdict.REVIEW_MED,
        "base_explanation": "損害賠償条項。条件・範囲の確認が必要",
        "check_points": [
            "賠償範囲（直接損害/間接損害）",
            "賠償上限の有無",
            "因果関係の要件"
        ],
        "legal_basis": "民法415条、416条",
        
        "mitigating_modifiers": [
            {
                "pattern": r"(直接|通常).{0,5}(損害|かつ現実に生じた)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "直接損害に限定しており、予見可能性の範囲内"
            },
            {
                "pattern": r"(上限|限度|Cap).{0,20}(12|１２|12ヶ月|1年|過去.{0,5}年).{0,10}(利用料|料金|対価)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "標準的な賠償上限（12ヶ月分の利用料）"
            },
        ],
        
        "aggravating_modifiers": [
            {
                "pattern": r"(間接|派生|特別|逸失利益|機会損失)",
                "verdict_change": ContextVerdict.REVIEW_HIGH,
                "explanation": "間接損害・逸失利益を含む可能性。範囲が広い"
            },
            {
                "pattern": r"(予見.{0,5}有無.{0,5}問わず|予見可能性.{0,5}関わらず)",
                "verdict_change": ContextVerdict.NG,
                "explanation": "予見可能性を問わない賠償。民法416条の原則に反する"
            },
        ],
    },
    
    # =========================================================================
    # 解約・解除条項系
    # =========================================================================
    "termination_clause": {
        "base_pattern": r"(解約|解除|契約.{0,3}終了).{0,10}(できる|する|行う)",
        "base_verdict": ContextVerdict.REVIEW_MED,
        "base_explanation": "解約・解除条項。条件・手続きの確認が必要",
        "check_points": [
            "解約事由の明確性",
            "予告期間の妥当性",
            "双方向性（相手方も解約できるか）"
        ],
        "legal_basis": "民法540条〜548条",
        
        "mitigating_modifiers": [
            {
                "pattern": r"(30|３０|30日|1ヶ月).{0,10}(前|以前).{0,10}(書面|通知|予告)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "30日前予告による解約。標準的な解約条件"
            },
            {
                "pattern": r"(双方|いずれの当事者も|甲乙いずれも)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "双方に解約権があり、均衡が取れている"
            },
            {
                "pattern": r"(催告|是正.{0,5}機会|猶予期間)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "催告・是正機会の規定あり。手続保障が確保されている"
            },
        ],
        
        "aggravating_modifiers": [
            {
                "pattern": r"(いつでも|理由.{0,5}なく|事前.{0,5}なく|直ちに)",
                "verdict_change": ContextVerdict.REVIEW_HIGH,
                "explanation": "無条件・即時解約権。一方的な契約終了リスク"
            },
            {
                "pattern": r"(当社|甲|弊社).{0,10}(のみ|だけ|に限り)",
                "verdict_change": ContextVerdict.NG,
                "explanation": "一方当事者のみに解約権。著しい不均衡"
            },
        ],
    },
    
    # =========================================================================
    # 規約変更条項系
    # =========================================================================
    "tos_modification": {
        "base_pattern": r"(規約|約款|条件).{0,10}(変更|改定|改正)",
        "base_verdict": ContextVerdict.REVIEW_MED,
        "base_explanation": "規約変更条項。変更手続き・効力発生条件の確認が必要",
        "check_points": [
            "変更の事前通知有無",
            "通知期間の長さ",
            "変更に対する異議申立・解約権"
        ],
        "legal_basis": "民法548条の4",
        
        "mitigating_modifiers": [
            {
                "pattern": r"(30|３０|30日|1ヶ月).{0,10}(前|以前).{0,10}(通知|告知|お知らせ)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "30日前通知規定あり。民法548条の4の要件を満たす可能性"
            },
            {
                "pattern": r"(同意.{0,5}ない|異議.{0,5}ある|承諾.{0,5}ない).{0,10}(場合|ときは?).{0,10}(解約|解除|退会)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "変更に同意しない場合の解約権が保障されている"
            },
            {
                "pattern": r"(軽微|形式的|事務的).{0,10}(変更|修正).{0,10}(に限|についてのみ)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "軽微な変更のみ。実質的内容の変更は含まない"
            },
        ],
        
        "aggravating_modifiers": [
            {
                "pattern": r"(いつでも|自由に|当社.{0,5}判断.{0,5}のみ)",
                "verdict_change": ContextVerdict.NG_CRITICAL,
                "explanation": "無制限の規約変更権。消費者契約法10条で無効"
            },
            {
                "pattern": r"(通知.{0,5}なく|事前.{0,5}なく|予告.{0,5}なく)",
                "verdict_change": ContextVerdict.NG,
                "explanation": "事前通知なしの変更。民法548条の4違反"
            },
        ],
    },
    
    # =========================================================================
    # 秘密保持条項系
    # =========================================================================
    "confidentiality_clause": {
        "base_pattern": r"(秘密|機密|Confidential).{0,10}(保持|保護|守秘|管理)",
        "base_verdict": ContextVerdict.REVIEW_MED,
        "base_explanation": "秘密保持条項。範囲・期間の確認が必要",
        "check_points": [
            "秘密情報の定義・範囲",
            "保持期間",
            "例外規定の有無"
        ],
        "legal_basis": "不正競争防止法2条6項",
        
        "mitigating_modifiers": [
            {
                "pattern": r"(秘密.{0,5}として.{0,5}明示|機密.{0,5}マーク|Confidential.{0,5}表示)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "秘密情報が明示的に特定されている"
            },
            {
                "pattern": r"(公知|公開情報|独自.{0,5}開発).{0,10}(除く|除外|含まない)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "標準的な例外規定あり"
            },
            {
                "pattern": r"(契約終了|終了後).{0,10}(\d+)\s*(年|ヶ年).{0,10}(まで|間|以内)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "保持期間が明確に定められている"
            },
        ],
        
        "aggravating_modifiers": [
            {
                "pattern": r"(一切|すべて|全て|あらゆる).{0,10}(情報|知識|知り得た)",
                "verdict_change": ContextVerdict.REVIEW_HIGH,
                "explanation": "秘密情報の範囲が過度に広い可能性"
            },
            {
                "pattern": r"(永久|永続|無期限|期限.{0,5}なく)",
                "verdict_change": ContextVerdict.NG,
                "explanation": "無期限の秘密保持義務。合理性を欠く"
            },
        ],
    },
    
    # =========================================================================
    # 競業避止条項系
    # =========================================================================
    "non_compete_clause": {
        "base_pattern": r"(競業|競合|同業).{0,10}(禁止|避止|してはならない)",
        "base_verdict": ContextVerdict.REVIEW_HIGH,
        "base_explanation": "競業避止条項。範囲・期間・代償措置の確認が必須",
        "check_points": [
            "期間の妥当性（2年以内が目安）",
            "地理的範囲の合理性",
            "代償措置の有無"
        ],
        "legal_basis": "憲法22条、判例法理",
        
        "mitigating_modifiers": [
            {
                "pattern": r"(1|2|一|二)\s*(年|ヶ年|年間).{0,10}(以内|を超えない|間)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "期間が2年以内で合理的な範囲"
            },
            {
                "pattern": r"(代償|補償|対価|手当).{0,10}(措置|として|支払)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "代償措置があり、有効性が高まる"
            },
            {
                "pattern": r"(当社.{0,5}事業所|○○県内|特定.{0,5}地域|限定.{0,5}地域)",
                "verdict_change": ContextVerdict.OK_CONDITIONAL,
                "explanation": "地理的範囲が合理的に限定されている"
            },
        ],
        
        "aggravating_modifiers": [
            {
                "pattern": r"([3-9]|\d{2,})\s*(年|ヶ年|年間)",
                "verdict_change": ContextVerdict.NG,
                "explanation": "競業避止期間が3年以上。無効となる可能性が高い"
            },
            {
                "pattern": r"(全国|日本国内|国内外|全世界|すべての地域)",
                "verdict_change": ContextVerdict.NG,
                "explanation": "地理的範囲が過度に広い。無効となる可能性が高い"
            },
            {
                "pattern": r"(代償|補償|対価).{0,10}(なし|ない|なく|設けない)",
                "verdict_change": ContextVerdict.NG,
                "explanation": "代償措置なしの競業避止。有効性に重大な疑問"
            },
        ],
    },
}


# =============================================================================
# メインエンジン
# =============================================================================

class ContextAwareEngine:
    """文脈依存判定エンジン"""
    
    VERSION = "1.59.0"
    
    def __init__(self):
        self.triggers = CONTEXT_TRIGGERS
    
    def analyze(self, clause_text: str, surrounding_context: str = "") -> List[ContextAwareResult]:
        """文脈を考慮した条項分析"""
        results = []
        
        # 分析対象テキスト（条項本体 + 周辺文脈）
        full_text = f"{surrounding_context} {clause_text}"
        
        for trigger_name, trigger_info in self.triggers.items():
            # ベースパターンのマッチ
            base_match = re.search(trigger_info["base_pattern"], clause_text)
            if not base_match:
                continue
            
            base_verdict = trigger_info["base_verdict"]
            final_verdict = base_verdict
            modifiers_found = []
            context_explanations = []
            
            # 緩和条件のチェック
            for modifier in trigger_info.get("mitigating_modifiers", []):
                if re.search(modifier["pattern"], full_text):
                    modifiers_found.append(f"[緩和] {modifier['explanation']}")
                    # 緩和方向に判定変更（より軽い判定へ）
                    if self._is_lighter_verdict(modifier["verdict_change"], final_verdict):
                        final_verdict = modifier["verdict_change"]
                        context_explanations.append(modifier["explanation"])
            
            # 強化条件のチェック（緩和より優先）
            for modifier in trigger_info.get("aggravating_modifiers", []):
                if re.search(modifier["pattern"], full_text):
                    modifiers_found.append(f"[強化] {modifier['explanation']}")
                    # 強化方向に判定変更（より重い判定へ）
                    if self._is_heavier_verdict(modifier["verdict_change"], final_verdict):
                        final_verdict = modifier["verdict_change"]
                        context_explanations.append(modifier["explanation"])
            
            # 結果生成
            context_explanation = trigger_info["base_explanation"]
            if context_explanations:
                context_explanation += f" → {'; '.join(context_explanations)}"
            
            results.append(ContextAwareResult(
                base_verdict=base_verdict,
                final_verdict=final_verdict,
                trigger_name=trigger_name,
                matched_base_text=base_match.group(0),
                modifiers_found=modifiers_found,
                context_explanation=context_explanation,
                check_points=trigger_info["check_points"],
                legal_basis=trigger_info["legal_basis"]
            ))
        
        return results
    
    def _is_lighter_verdict(self, new: ContextVerdict, current: ContextVerdict) -> bool:
        """新しい判定が現在より軽いかどうか"""
        priority = [
            ContextVerdict.NG_CRITICAL,
            ContextVerdict.NG,
            ContextVerdict.REVIEW_HIGH,
            ContextVerdict.REVIEW_MED,
            ContextVerdict.OK_CONDITIONAL,
            ContextVerdict.OK,
        ]
        return priority.index(new) > priority.index(current)
    
    def _is_heavier_verdict(self, new: ContextVerdict, current: ContextVerdict) -> bool:
        """新しい判定が現在より重いかどうか"""
        priority = [
            ContextVerdict.NG_CRITICAL,
            ContextVerdict.NG,
            ContextVerdict.REVIEW_HIGH,
            ContextVerdict.REVIEW_MED,
            ContextVerdict.OK_CONDITIONAL,
            ContextVerdict.OK,
        ]
        return priority.index(new) < priority.index(current)
    
    def get_statistics(self) -> Dict:
        """統計情報"""
        total_triggers = len(self.triggers)
        total_mitigating = sum(
            len(t.get("mitigating_modifiers", [])) 
            for t in self.triggers.values()
        )
        total_aggravating = sum(
            len(t.get("aggravating_modifiers", [])) 
            for t in self.triggers.values()
        )
        
        return {
            "version": self.VERSION,
            "total_context_triggers": total_triggers,
            "total_mitigating_modifiers": total_mitigating,
            "total_aggravating_modifiers": total_aggravating,
            "trigger_names": list(self.triggers.keys())
        }


# エクスポート
context_aware_engine = ContextAwareEngine()
