"""
VERITAS v160 Core Module
パターン精度向上 + ToDo圧縮強化版

v159機能:
- エッジケース検出（25種）
- 業界別ホワイトリスト（32種/6ドメイン）
- 文脈依存判定（6トリガー）

v160新機能:
- 高度ToDo圧縮（90%達成）
- 多段連鎖パターン（11種）
- 相互参照解決
- 階層構造認識
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

__version__ = "1.60.0"
