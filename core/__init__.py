"""
VERITAS v167 Core Module
全機能統合版（Phase 1-6A + v163弁護士思考分解）

v159機能:
- エッジケース検出（25種）
- 業界別ホワイトリスト（32種/6ドメイン）
- 文脈依存判定（6トリガー）

v160新機能:
- 高度ToDo圧縮（90%達成）
- 多段連鎖パターン（11種）
- 相互参照解決
- 階層構造認識

v163新機能（弁護士思考分解）:
- 曖昧性検出（AMBIGUOUS_CLAUSE）
- 条項間整合性チェック（COHERENCE_CHECK）
- 期間未定義検出（NO_TIME_LIMIT）
- 弁護士指摘6/6項目(100%)自動検出達成
"""

# v159モジュール
from .edge_cases import (
    edge_case_detector,
    EdgeCaseDetector,
    EdgeCaseResult,
    EdgeVerdict
)

from .whitelist_patterns import (
    industry_whitelist,
    IndustryWhitelist,
    WhitelistResult,
    WhitelistVerdict
)

from .context_aware import (
    context_aware_engine,
    ContextAwareEngine,
    ContextAwareResult,
    ContextVerdict
)

from .pattern_engine import (
    unified_pattern_engine,
    UnifiedPatternEngine,
    UnifiedAnalysisResult,
    UnifiedVerdict,
    quick_analyze
)

# v160モジュール
from .todo_compression import (
    TodoItem,
    TodoGroup,
    CompressionResult,
    AdvancedTodoCompressor,
    compress_todos,
    normalize_text,
    get_canonical_domain,
    extract_cross_references,
    detect_hierarchy,
    get_compression_stats,
    SYNONYM_MAPS,
    CHAIN_PATTERNS,
    ChainType,
)

__version__ = "1.67.0"

# v163モジュール（弁護士思考分解）
from .lawyer_thinking import (
    # 曖昧性検出
    analyze_ambiguity,
    AmbiguityResult,
    AmbiguityType,
    format_ambiguity_output,
    # 条項間整合性
    analyze_contract_coherence,
    CoherenceResult,
    ClauseInfo,
    EffectTag,
    format_coherence_output,
    # 期間未定義
    analyze_contract_time_limits,
    TimeLimitResult,
    ClauseCategory,
    format_time_limit_output,
)
