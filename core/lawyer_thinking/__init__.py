"""
VERITAS v167 - Lawyer Thinking Module
弁護士思考構造分解実装（シエル殿設計）

v163で追加された新機能:
1. 曖昧性検出 (AMBIGUOUS_CLAUSE)
2. 条項間整合性チェック (COHERENCE_CHECK)
3. 期間未定義検出 (NO_TIME_LIMIT)

実証結果: 弁護士指摘6/6項目(100%)自動検出
"""

from .ambiguity_detector import (
    analyze_clause as analyze_ambiguity,
    AmbiguityResult,
    AmbiguityType,
    format_output as format_ambiguity_output
)

from .clause_coherence_checker import (
    analyze_contract_coherence,
    CoherenceResult,
    ClauseInfo,
    EffectTag,
    format_output as format_coherence_output
)

from .time_limit_detector import (
    analyze_contract_time_limits,
    TimeLimitResult,
    ClauseCategory,
    format_output as format_time_limit_output
)

__all__ = [
    # 曖昧性検出
    'analyze_ambiguity',
    'AmbiguityResult',
    'AmbiguityType',
    'format_ambiguity_output',
    
    # 条項間整合性
    'analyze_contract_coherence',
    'CoherenceResult',
    'ClauseInfo',
    'EffectTag',
    'format_coherence_output',
    
    # 期間未定義
    'analyze_contract_time_limits',
    'TimeLimitResult',
    'ClauseCategory',
    'format_time_limit_output',
]
