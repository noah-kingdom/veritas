"""
VERITAS v159 - Unified Pattern Engine
統合パターンエンジン

3軸の統合:
1. Edge Cases (エッジケース検出)
2. Industry Whitelist (業界別ホワイトリスト)
3. Context-Aware (文脈依存判定)

判定フロー:
1. ホワイトリストチェック → 該当すれば早期OK
2. エッジケースチェック → 危険パターン検出
3. 文脈依存判定 → 微妙なラインの最終判定
4. 総合判定 → 最も厳しい判定を採用

設計原則:
- FALSE_OK=0 の死守
- REVIEW率の適正化（過度な誤検知削減）
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# 各モジュールのインポート
from .edge_cases import edge_case_detector, EdgeCaseResult, EdgeVerdict
from .whitelist_patterns import industry_whitelist, WhitelistResult, WhitelistVerdict
from .context_aware import context_aware_engine, ContextAwareResult, ContextVerdict


class UnifiedVerdict(Enum):
    """統合判定結果"""
    NG_CRITICAL = "NG_CRITICAL"      # 重大違反（即時対応必須）
    NG = "NG"                         # 違反・無効リスク
    REVIEW_HIGH = "REVIEW_HIGH"       # 高リスク要確認
    REVIEW_MED = "REVIEW_MED"         # 中リスク要確認
    OK_CONDITIONAL = "OK_CONDITIONAL" # 条件付きOK
    OK_STANDARD = "OK_STANDARD"       # 業界標準で安全
    OK_COMPLIANT = "OK_COMPLIANT"     # 法令準拠で安全
    OK_SAFE = "OK_SAFE"               # 明確に安全
    OK = "OK"                         # 問題なし


@dataclass
class UnifiedAnalysisResult:
    """統合分析結果"""
    clause_text: str
    final_verdict: UnifiedVerdict
    confidence: float                  # 0.0 - 1.0
    
    # 各エンジンの結果
    whitelist_results: List[WhitelistResult] = field(default_factory=list)
    edge_case_results: List[EdgeCaseResult] = field(default_factory=list)
    context_results: List[ContextAwareResult] = field(default_factory=list)
    
    # 総合情報
    check_points: List[str] = field(default_factory=list)
    legal_basis: List[str] = field(default_factory=list)
    risk_summary: str = ""
    rewrite_suggestions: List[str] = field(default_factory=list)
    
    # メタ情報
    analysis_timestamp: str = ""
    engine_version: str = ""


class UnifiedPatternEngine:
    """統合パターンエンジン"""
    
    VERSION = "1.59.0"
    
    def __init__(self):
        self.edge_detector = edge_case_detector
        self.whitelist = industry_whitelist
        self.context_engine = context_aware_engine
        
        # 判定優先度（重い順）
        self.verdict_priority = [
            UnifiedVerdict.NG_CRITICAL,
            UnifiedVerdict.NG,
            UnifiedVerdict.REVIEW_HIGH,
            UnifiedVerdict.REVIEW_MED,
            UnifiedVerdict.OK_CONDITIONAL,
            UnifiedVerdict.OK_STANDARD,
            UnifiedVerdict.OK_COMPLIANT,
            UnifiedVerdict.OK_SAFE,
            UnifiedVerdict.OK,
        ]
    
    def analyze(
        self, 
        clause_text: str, 
        domain: Optional[str] = None,
        surrounding_context: str = ""
    ) -> UnifiedAnalysisResult:
        """
        統合分析を実行
        
        Args:
            clause_text: 分析対象の条項テキスト
            domain: ドメイン指定（LABOR, REALESTATE, IT_SAAS等）
            surrounding_context: 周辺文脈（前後の条項等）
        
        Returns:
            UnifiedAnalysisResult: 統合分析結果
        """
        # 結果初期化
        result = UnifiedAnalysisResult(
            clause_text=clause_text,
            final_verdict=UnifiedVerdict.OK,
            confidence=1.0,
            analysis_timestamp=datetime.now().isoformat(),
            engine_version=self.VERSION
        )
        
        collected_verdicts = []
        
        # =========================================================================
        # Step 1: ホワイトリストチェック
        # =========================================================================
        whitelist_results = self.whitelist.detect(clause_text, domain)
        result.whitelist_results = whitelist_results
        
        if whitelist_results:
            # ホワイトリストにヒット → 基本的に安全だが確認は継続
            for wr in whitelist_results:
                unified_verdict = self._convert_whitelist_verdict(wr.verdict)
                collected_verdicts.append(unified_verdict)
                result.check_points.append(f"[ホワイトリスト] {wr.reason}")
                result.legal_basis.append(wr.legal_basis)
        
        # =========================================================================
        # Step 2: エッジケースチェック
        # =========================================================================
        edge_results = self.edge_detector.detect(clause_text)
        result.edge_case_results = edge_results
        
        for er in edge_results:
            unified_verdict = self._convert_edge_verdict(er.verdict)
            collected_verdicts.append(unified_verdict)
            result.check_points.extend(er.check_points)
            result.legal_basis.append(er.legal_basis)
            if er.rewrite_suggestion:
                result.rewrite_suggestions.append(er.rewrite_suggestion)
        
        # =========================================================================
        # Step 3: 文脈依存判定
        # =========================================================================
        context_results = self.context_engine.analyze(clause_text, surrounding_context)
        result.context_results = context_results
        
        for cr in context_results:
            unified_verdict = self._convert_context_verdict(cr.final_verdict)
            collected_verdicts.append(unified_verdict)
            result.check_points.extend(cr.check_points)
            result.legal_basis.append(cr.legal_basis)
            result.check_points.append(f"[文脈判定] {cr.context_explanation}")
        
        # =========================================================================
        # Step 4: 最終判定（最も厳しい判定を採用）
        # =========================================================================
        if collected_verdicts:
            result.final_verdict = self._get_worst_verdict(collected_verdicts)
            result.confidence = self._calculate_confidence(result)
        else:
            # 何も検出されなかった場合
            result.final_verdict = UnifiedVerdict.OK
            result.confidence = 0.7  # 検出なし = 中程度の確信
        
        # リスクサマリー生成
        result.risk_summary = self._generate_risk_summary(result)
        
        # 重複除去
        result.check_points = list(dict.fromkeys(result.check_points))
        result.legal_basis = list(dict.fromkeys(result.legal_basis))
        result.rewrite_suggestions = list(dict.fromkeys(result.rewrite_suggestions))
        
        return result
    
    def _convert_whitelist_verdict(self, verdict: WhitelistVerdict) -> UnifiedVerdict:
        """ホワイトリスト判定を統合判定に変換"""
        mapping = {
            WhitelistVerdict.OK_SAFE: UnifiedVerdict.OK_SAFE,
            WhitelistVerdict.OK_STANDARD: UnifiedVerdict.OK_STANDARD,
            WhitelistVerdict.OK_COMPLIANT: UnifiedVerdict.OK_COMPLIANT,
            WhitelistVerdict.OK_CAUTION: UnifiedVerdict.OK_CONDITIONAL,
        }
        return mapping.get(verdict, UnifiedVerdict.OK)
    
    def _convert_edge_verdict(self, verdict: EdgeVerdict) -> UnifiedVerdict:
        """エッジケース判定を統合判定に変換"""
        mapping = {
            EdgeVerdict.NG_CRITICAL: UnifiedVerdict.NG_CRITICAL,
            EdgeVerdict.NG: UnifiedVerdict.NG,
            EdgeVerdict.REVIEW_HIGH: UnifiedVerdict.REVIEW_HIGH,
            EdgeVerdict.REVIEW_MED: UnifiedVerdict.REVIEW_MED,
        }
        return mapping.get(verdict, UnifiedVerdict.REVIEW_MED)
    
    def _convert_context_verdict(self, verdict: ContextVerdict) -> UnifiedVerdict:
        """文脈判定を統合判定に変換"""
        mapping = {
            ContextVerdict.NG_CRITICAL: UnifiedVerdict.NG_CRITICAL,
            ContextVerdict.NG: UnifiedVerdict.NG,
            ContextVerdict.REVIEW_HIGH: UnifiedVerdict.REVIEW_HIGH,
            ContextVerdict.REVIEW_MED: UnifiedVerdict.REVIEW_MED,
            ContextVerdict.OK_CONDITIONAL: UnifiedVerdict.OK_CONDITIONAL,
            ContextVerdict.OK: UnifiedVerdict.OK,
            ContextVerdict.UNDETERMINED: UnifiedVerdict.REVIEW_MED,
        }
        return mapping.get(verdict, UnifiedVerdict.REVIEW_MED)
    
    def _get_worst_verdict(self, verdicts: List[UnifiedVerdict]) -> UnifiedVerdict:
        """最も厳しい判定を返す"""
        for priority_verdict in self.verdict_priority:
            if priority_verdict in verdicts:
                return priority_verdict
        return UnifiedVerdict.OK
    
    def _calculate_confidence(self, result: UnifiedAnalysisResult) -> float:
        """判定の確信度を計算"""
        confidence = 1.0
        
        # 複数のエンジンが同じ結論 → 確信度UP
        verdict_sources = 0
        if result.whitelist_results:
            verdict_sources += 1
        if result.edge_case_results:
            verdict_sources += 1
        if result.context_results:
            verdict_sources += 1
        
        if verdict_sources >= 2:
            confidence = min(1.0, confidence + 0.1)
        
        # 文脈条件が多く見つかった → 確信度UP
        if result.context_results:
            total_modifiers = sum(
                len(cr.modifiers_found) for cr in result.context_results
            )
            if total_modifiers >= 2:
                confidence = min(1.0, confidence + 0.05 * total_modifiers)
        
        # NG_CRITICALの場合は常に高確信度
        if result.final_verdict == UnifiedVerdict.NG_CRITICAL:
            confidence = max(confidence, 0.95)
        
        return round(confidence, 2)
    
    def _generate_risk_summary(self, result: UnifiedAnalysisResult) -> str:
        """リスクサマリーを生成"""
        verdict = result.final_verdict
        
        summaries = {
            UnifiedVerdict.NG_CRITICAL: "【重大リスク】法令違反または無効条項の可能性が高い。即時対応が必要。",
            UnifiedVerdict.NG: "【高リスク】無効または不当条項の可能性。修正を強く推奨。",
            UnifiedVerdict.REVIEW_HIGH: "【要確認・高】重要な確認事項あり。法務担当者のレビューを推奨。",
            UnifiedVerdict.REVIEW_MED: "【要確認・中】確認すべき点あり。内容を精査のこと。",
            UnifiedVerdict.OK_CONDITIONAL: "【条件付きOK】一定の条件下で問題なし。条件の充足を確認。",
            UnifiedVerdict.OK_STANDARD: "【OK】業界標準に準拠した条項。",
            UnifiedVerdict.OK_COMPLIANT: "【OK】法令に準拠した条項。",
            UnifiedVerdict.OK_SAFE: "【OK】安全な条項。",
            UnifiedVerdict.OK: "【OK】特に問題なし。",
        }
        
        return summaries.get(verdict, "判定結果を確認してください。")
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報"""
        edge_stats = self.edge_detector.get_statistics()
        whitelist_stats = self.whitelist.get_statistics()
        context_stats = self.context_engine.get_statistics()
        
        return {
            "engine_version": self.VERSION,
            "total_patterns": (
                edge_stats["total_edge_patterns"] +
                whitelist_stats["total_whitelist_patterns"] +
                context_stats["total_context_triggers"]
            ),
            "edge_cases": edge_stats,
            "whitelist": whitelist_stats,
            "context_aware": context_stats,
            "patent_map": ["CLAIM_1", "CLAIM_2", "CLAIM_3", "CLAIM_4", "CLAIM_5", "CLAIM_6"]
        }


# エクスポート
unified_pattern_engine = UnifiedPatternEngine()


# =============================================================================
# 便利関数
# =============================================================================

def quick_analyze(clause_text: str, domain: Optional[str] = None) -> Dict:
    """簡易分析（辞書形式で結果を返す）"""
    result = unified_pattern_engine.analyze(clause_text, domain)
    
    return {
        "verdict": result.final_verdict.value,
        "confidence": result.confidence,
        "risk_summary": result.risk_summary,
        "check_points": result.check_points,
        "legal_basis": result.legal_basis,
        "rewrite_suggestions": result.rewrite_suggestions,
        "details": {
            "whitelist_hits": len(result.whitelist_results),
            "edge_case_hits": len(result.edge_case_results),
            "context_hits": len(result.context_results),
        }
    }
