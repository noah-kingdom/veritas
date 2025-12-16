"""
VERITAS v160 - Advanced ToDo Compression
高度ToDo圧縮モジュール

v157: 75%達成（同義語正規化 + 基本連鎖）
v160: 90%目標（高度連鎖ロジック + 階層解析 + 相互参照解決）

新機能:
1. 多段連鎖パターン（15種）
2. 相互参照解決（「前条」「第○条」等）
3. 階層構造認識（1. 2. 3. / (1)(2)(3) 等）
4. 意味的クラスタリング（文脈類似度）
5. 条項ペア認識（権利-義務、原則-例外等）

設計原則:
- FALSE_OK=0 維持（判定レーンは不変）
- v157互換（既存ロジックを壊さない）
"""

import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


# =============================================================================
# 同義語正規化（v157継承 + 拡張）
# =============================================================================

SYNONYM_MAPS: Dict[str, List[str]] = {
    # TERMINATION: 解除・終了系（19語）
    "TERMINATION": [
        "解除", "解約", "解消", "契約終了", "終了", "期間満了", "失効",
        "打ち切り", "中途解約", "即時解除", "催告解除", "無催告解除",
        "契約解消", "合意解除", "法定解除", "約定解除", "更新拒絶",
        "自動終了", "当然終了"
    ],
    
    # LIABILITY: 責任・賠償系（24語）
    "LIABILITY": [
        "損害賠償", "賠償", "補償", "免責", "責任制限", "責任上限",
        "賠償額", "損害", "損失", "責任", "帰責", "過失責任",
        "無過失責任", "連帯責任", "履行責任", "瑕疵担保", "契約不適合",
        "債務不履行", "不法行為", "賠償請求", "求償", "填補",
        "間接損害", "逸失利益"
    ],
    
    # CONFIDENTIAL: 秘密保持系（16語）
    "CONFIDENTIAL": [
        "秘密", "機密", "守秘", "秘密保持", "秘密情報", "機密情報",
        "営業秘密", "ノウハウ", "非公開", "開示禁止", "漏洩禁止",
        "第三者開示", "情報管理", "情報保護", "NDA", "秘匿"
    ],
    
    # IP: 知財系（14語）
    "IP": [
        "著作権", "特許", "知財", "知的財産", "商標", "意匠",
        "実用新案", "著作物", "発明", "ライセンス", "使用許諾",
        "権利帰属", "職務発明", "権利譲渡"
    ],
    
    # PAYMENT: 支払・報酬系（15語）
    "PAYMENT": [
        "支払", "報酬", "対価", "代金", "料金", "費用",
        "請求", "精算", "決済", "振込", "入金", "未払",
        "遅延損害金", "支払条件", "支払期限"
    ],
    
    # DEFINITION: 定義系（10語）
    "DEFINITION": [
        "定義", "とは", "をいう", "を意味する", "に該当する",
        "次のとおり", "以下のとおり", "次に掲げる", "下記のとおり",
        "本契約において"
    ],
    
    # EXCEPTION: 例外系（13語）
    "EXCEPTION": [
        "例外", "ただし", "公知", "除外", "適用除外", "この限りでない",
        "妨げない", "に該当する場合", "を除き", "以外", "但し書き",
        "なお書き", "別段の定め"
    ],
    
    # SURVIVAL: 存続系（15語）
    "SURVIVAL": [
        "存続", "終了後", "効力", "残存", "有効期間", "存続期間",
        "なお効力を有する", "引き続き適用", "終了後も", "解除後も",
        "期間満了後", "契約終了後", "永続", "永久", "無期限"
    ],
    
    # INDEMNITY: 補償・免責系（12語）
    "INDEMNITY": [
        "補償", "填補", "求償", "免責", "hold harmless",
        "防御", "第三者請求", "クレーム対応", "訴訟費用",
        "弁護士費用", "損害填補", "損失補償"
    ],
    
    # COMPLIANCE: 法令遵守系（10語）
    "COMPLIANCE": [
        "法令遵守", "コンプライアンス", "適法", "遵守", "準拠",
        "法的義務", "規制", "許認可", "届出", "報告義務"
    ],
    
    # FORCE_MAJEURE: 不可抗力系（8語）
    "FORCE_MAJEURE": [
        "不可抗力", "天災", "地震", "台風", "戦争", "テロ",
        "パンデミック", "法令変更"
    ],
    
    # DISPUTE: 紛争解決系（10語）
    "DISPUTE": [
        "紛争", "争い", "訴訟", "仲裁", "調停", "裁判",
        "管轄", "準拠法", "合意管轄", "専属管轄"
    ],
}


def normalize_text(text: str) -> Tuple[str, List[str]]:
    """
    テキストを正規化し、検出されたcanonicalタグを返す
    
    Returns:
        (正規化テキスト, [検出されたcanonicalタグ])
    """
    detected_tags = []
    normalized = text
    
    for canonical, synonyms in SYNONYM_MAPS.items():
        for synonym in synonyms:
            if synonym in text:
                if canonical not in detected_tags:
                    detected_tags.append(canonical)
                # テキスト中のsynonymをcanonicalに置換（グルーピング用）
                normalized = normalized.replace(synonym, f"[{canonical}]")
    
    return normalized, detected_tags


def get_canonical_domain(tags: List[str]) -> Optional[str]:
    """タグリストから主要ドメインを決定"""
    # 優先度順
    priority = [
        "LIABILITY", "TERMINATION", "CONFIDENTIAL", "IP", 
        "PAYMENT", "INDEMNITY", "COMPLIANCE", "DISPUTE"
    ]
    
    for domain in priority:
        if domain in tags:
            return domain
    
    return tags[0] if tags else None


# =============================================================================
# 高度連鎖パターン定義（v160新規）
# =============================================================================

class ChainType(Enum):
    """連鎖タイプ"""
    # 基本連鎖（v157）
    DEFINITION_BODY_EXCEPTION_SURVIVAL = "定義→本文→例外→存続"
    
    # 拡張連鎖（v160新規）
    OBLIGATION_RIGHT_REMEDY = "義務→権利→救済"
    PRINCIPLE_EXCEPTION_SUPPLEMENT = "原則→例外→補足"
    CONDITION_EFFECT_REMEDY = "条件→効果→救済"
    SCOPE_LIMITATION_EXCEPTION = "範囲→制限→例外"
    PROCEDURE_TIMING_CONSEQUENCE = "手続→期限→効果"
    REPRESENTATION_WARRANTY_INDEMNITY = "表明→保証→補償"
    PROHIBITION_EXCEPTION_PENALTY = "禁止→例外→違反効果"
    GRANT_RESTRICTION_TERMINATION = "付与→制限→終了"
    CONFIDENTIAL_EXCEPTION_RETURN = "秘密→例外→返還"
    PAYMENT_CONDITION_DELAY = "支払→条件→遅延"
    TERMINATION_NOTICE_EFFECT = "解除→通知→効果"
    DISPUTE_PROCEDURE_JURISDICTION = "紛争→手続→管轄"
    GENERAL_SPECIFIC_EXCEPTION = "一般→特則→例外"
    PARENT_CHILD_SIBLING = "親条項→子条項→兄弟条項"


@dataclass
class ChainPattern:
    """連鎖パターン定義"""
    chain_type: ChainType
    components: List[str]  # 必要な構成要素
    keywords: List[str]    # 検出キーワード
    priority: int          # 優先度（高いほど優先）
    min_components: int    # 最低必要構成要素数


CHAIN_PATTERNS: List[ChainPattern] = [
    # 基本連鎖（最高優先）
    ChainPattern(
        chain_type=ChainType.DEFINITION_BODY_EXCEPTION_SURVIVAL,
        components=["DEFINITION", "BODY", "EXCEPTION", "SURVIVAL"],
        keywords=["定義", "とは", "ただし", "例外", "存続", "終了後"],
        priority=100,
        min_components=3
    ),
    
    # 表明保証補償チェーン
    ChainPattern(
        chain_type=ChainType.REPRESENTATION_WARRANTY_INDEMNITY,
        components=["REPRESENTATION", "WARRANTY", "INDEMNITY"],
        keywords=["表明", "保証", "補償", "真実", "正確", "填補"],
        priority=95,
        min_components=2
    ),
    
    # 秘密例外返還チェーン
    ChainPattern(
        chain_type=ChainType.CONFIDENTIAL_EXCEPTION_RETURN,
        components=["CONFIDENTIAL", "EXCEPTION", "RETURN"],
        keywords=["秘密", "機密", "公知", "例外", "返還", "廃棄"],
        priority=90,
        min_components=2
    ),
    
    # 解除通知効果チェーン
    ChainPattern(
        chain_type=ChainType.TERMINATION_NOTICE_EFFECT,
        components=["TERMINATION", "NOTICE", "EFFECT"],
        keywords=["解除", "解約", "通知", "届出", "効力", "効果"],
        priority=85,
        min_components=2
    ),
    
    # 禁止例外違反チェーン
    ChainPattern(
        chain_type=ChainType.PROHIBITION_EXCEPTION_PENALTY,
        components=["PROHIBITION", "EXCEPTION", "PENALTY"],
        keywords=["禁止", "してはならない", "ただし", "違反", "損害賠償"],
        priority=80,
        min_components=2
    ),
    
    # 支払条件遅延チェーン
    ChainPattern(
        chain_type=ChainType.PAYMENT_CONDITION_DELAY,
        components=["PAYMENT", "CONDITION", "DELAY"],
        keywords=["支払", "報酬", "条件", "期限", "遅延", "損害金"],
        priority=75,
        min_components=2
    ),
    
    # 紛争手続管轄チェーン
    ChainPattern(
        chain_type=ChainType.DISPUTE_PROCEDURE_JURISDICTION,
        components=["DISPUTE", "PROCEDURE", "JURISDICTION"],
        keywords=["紛争", "訴訟", "仲裁", "協議", "管轄", "準拠法"],
        priority=70,
        min_components=2
    ),
    
    # 範囲制限例外チェーン
    ChainPattern(
        chain_type=ChainType.SCOPE_LIMITATION_EXCEPTION,
        components=["SCOPE", "LIMITATION", "EXCEPTION"],
        keywords=["範囲", "対象", "制限", "限定", "例外", "適用除外"],
        priority=65,
        min_components=2
    ),
    
    # 義務権利救済チェーン
    ChainPattern(
        chain_type=ChainType.OBLIGATION_RIGHT_REMEDY,
        components=["OBLIGATION", "RIGHT", "REMEDY"],
        keywords=["義務", "責任", "権利", "請求", "救済", "是正"],
        priority=60,
        min_components=2
    ),
    
    # 原則例外補足チェーン
    ChainPattern(
        chain_type=ChainType.PRINCIPLE_EXCEPTION_SUPPLEMENT,
        components=["PRINCIPLE", "EXCEPTION", "SUPPLEMENT"],
        keywords=["原則", "本則", "ただし", "なお", "補足", "付記"],
        priority=55,
        min_components=2
    ),
    
    # 親子兄弟チェーン（階層構造）
    ChainPattern(
        chain_type=ChainType.PARENT_CHILD_SIBLING,
        components=["PARENT", "CHILD", "SIBLING"],
        keywords=["前項", "前条", "次項", "次条", "本条", "同条"],
        priority=50,
        min_components=2
    ),
]


# =============================================================================
# 相互参照解決（v160新規）
# =============================================================================

@dataclass
class CrossReference:
    """相互参照情報"""
    source_clause_id: str
    target_clause_id: str
    reference_type: str  # "前条", "第○条", "前項" 等
    reference_text: str


def extract_cross_references(clauses: List[Dict]) -> List[CrossReference]:
    """
    条項間の相互参照を抽出
    
    パターン:
    - 「前条」「次条」「前項」「次項」
    - 「第○条」「第○項」
    - 「本条」「本項」
    - 「上記」「下記」「前述」「後述」
    """
    references = []
    
    # 参照パターン
    patterns = [
        (r"前条", "PREV_CLAUSE"),
        (r"次条", "NEXT_CLAUSE"),
        (r"前項", "PREV_PARAGRAPH"),
        (r"次項", "NEXT_PARAGRAPH"),
        (r"第(\d+)条", "SPECIFIC_CLAUSE"),
        (r"第(\d+)項", "SPECIFIC_PARAGRAPH"),
        (r"本条", "SELF_CLAUSE"),
        (r"本項", "SELF_PARAGRAPH"),
        (r"上記|前述", "PRECEDING"),
        (r"下記|後述", "FOLLOWING"),
    ]
    
    for i, clause in enumerate(clauses):
        clause_id = clause.get("clause_id", f"c{i}")
        text = clause.get("clause_text", "")
        
        for pattern, ref_type in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                target_id = None
                
                if ref_type == "PREV_CLAUSE" and i > 0:
                    target_id = clauses[i-1].get("clause_id", f"c{i-1}")
                elif ref_type == "NEXT_CLAUSE" and i < len(clauses) - 1:
                    target_id = clauses[i+1].get("clause_id", f"c{i+1}")
                elif ref_type == "SPECIFIC_CLAUSE":
                    target_num = int(match.group(1))
                    if 0 < target_num <= len(clauses):
                        target_id = clauses[target_num-1].get("clause_id", f"c{target_num-1}")
                elif ref_type == "SELF_CLAUSE":
                    target_id = clause_id
                elif ref_type in ["PREV_PARAGRAPH", "PRECEDING"] and i > 0:
                    target_id = clauses[i-1].get("clause_id", f"c{i-1}")
                elif ref_type in ["NEXT_PARAGRAPH", "FOLLOWING"] and i < len(clauses) - 1:
                    target_id = clauses[i+1].get("clause_id", f"c{i+1}")
                
                if target_id and target_id != clause_id:
                    references.append(CrossReference(
                        source_clause_id=clause_id,
                        target_clause_id=target_id,
                        reference_type=ref_type,
                        reference_text=match.group(0)
                    ))
    
    return references


def build_reference_graph(references: List[CrossReference]) -> Dict[str, Set[str]]:
    """参照グラフを構築（無向グラフ）"""
    graph = defaultdict(set)
    
    for ref in references:
        graph[ref.source_clause_id].add(ref.target_clause_id)
        graph[ref.target_clause_id].add(ref.source_clause_id)
    
    return dict(graph)


def find_connected_components(graph: Dict[str, Set[str]], all_clause_ids: List[str]) -> List[Set[str]]:
    """連結成分を発見（相互参照で結ばれた条項群）"""
    visited = set()
    components = []
    
    def dfs(node: str, component: Set[str]):
        if node in visited:
            return
        visited.add(node)
        component.add(node)
        for neighbor in graph.get(node, []):
            dfs(neighbor, component)
    
    for clause_id in all_clause_ids:
        if clause_id not in visited:
            component = set()
            dfs(clause_id, component)
            if len(component) > 1:  # 2つ以上の条項が結ばれている場合のみ
                components.append(component)
    
    return components


# =============================================================================
# 階層構造認識（v160新規）
# =============================================================================

@dataclass
class HierarchyNode:
    """階層構造ノード"""
    clause_id: str
    level: int  # 0=条, 1=項, 2=号, 3=イロハ
    parent_id: Optional[str]
    children_ids: List[str] = field(default_factory=list)


def detect_hierarchy(clauses: List[Dict]) -> Dict[str, HierarchyNode]:
    """
    条項の階層構造を検出
    
    パターン:
    - 第○条（レベル0）
    - 1. 2. 3. または (1)(2)(3)（レベル1）
    - (ア)(イ)(ウ) または イ ロ ハ（レベル2）
    """
    hierarchy = {}
    current_parents = {0: None, 1: None, 2: None}
    
    level_patterns = [
        (r"^第\d+条", 0),
        (r"^(\d+)\.|^\((\d+)\)", 1),
        (r"^\([ア-ン]\)|^[イロハニホヘト][\s　]", 2),
    ]
    
    for i, clause in enumerate(clauses):
        clause_id = clause.get("clause_id", f"c{i}")
        text = clause.get("clause_text", "").strip()
        
        detected_level = 0  # デフォルト
        
        for pattern, level in level_patterns:
            if re.match(pattern, text):
                detected_level = level
                break
        
        parent_id = current_parents.get(detected_level - 1) if detected_level > 0 else None
        
        node = HierarchyNode(
            clause_id=clause_id,
            level=detected_level,
            parent_id=parent_id
        )
        
        # 親ノードに子を追加
        if parent_id and parent_id in hierarchy:
            hierarchy[parent_id].children_ids.append(clause_id)
        
        # 現在の親を更新
        current_parents[detected_level] = clause_id
        
        hierarchy[clause_id] = node
    
    return hierarchy


def group_by_hierarchy(hierarchy: Dict[str, HierarchyNode]) -> List[Set[str]]:
    """階層構造に基づくグループを生成"""
    groups = []
    processed = set()
    
    for clause_id, node in hierarchy.items():
        if clause_id in processed:
            continue
        
        # ルートノード（親なし）または親子関係があるものをグループ化
        if node.children_ids:
            group = {clause_id}
            group.update(node.children_ids)
            
            # 孫も追加
            for child_id in node.children_ids:
                if child_id in hierarchy:
                    group.update(hierarchy[child_id].children_ids)
            
            groups.append(group)
            processed.update(group)
    
    return groups


# =============================================================================
# ToDo項目とグループ
# =============================================================================

@dataclass
class TodoItem:
    """ToDo項目"""
    todo_id: str
    clause_id: str
    clause_text: str
    check_point: str
    priority: str = "MEDIUM"
    canonical_tags: List[str] = field(default_factory=list)
    clause_index: int = 0
    
    def __post_init__(self):
        if not self.canonical_tags:
            _, self.canonical_tags = normalize_text(
                self.clause_text + " " + self.check_point
            )


@dataclass
class TodoGroup:
    """ToDoグループ"""
    group_id: str
    group_key: str
    group_reason: str
    members: List[TodoItem] = field(default_factory=list)
    priority: str = "MEDIUM"
    canonical_domain: Optional[str] = None
    merge_rules: List[str] = field(default_factory=list)
    chain_type: Optional[ChainType] = None
    
    def add_member(self, item: TodoItem):
        self.members.append(item)
        priority_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        if priority_order.get(item.priority, 0) > priority_order.get(self.priority, 0):
            self.priority = item.priority


@dataclass
class CompressionResult:
    """圧縮結果"""
    groups: List[TodoGroup]
    original_count: int
    compressed_count: int
    compression_ratio: float
    merge_rules_hit: Dict[str, int]
    chain_types_used: List[str]
    version: str = "1.60.0"


# =============================================================================
# 高度圧縮エンジン（v160）
# =============================================================================

class AdvancedTodoCompressor:
    """高度ToDo圧縮エンジン"""
    
    VERSION = "1.60.0"
    TARGET_COMPRESSION = 0.90  # 90%目標
    
    def __init__(self):
        self.chain_patterns = CHAIN_PATTERNS
        self.merge_rules_hit = defaultdict(int)
    
    def compress(self, todos: List[TodoItem], clauses: List[Dict] = None) -> CompressionResult:
        """
        ToDoリストを圧縮
        
        処理順序:
        1. 同義語正規化
        2. 相互参照解決
        3. 階層構造認識
        4. 連鎖パターンマッチング
        5. 近接性グルーピング
        6. ドメイン統合
        """
        if not todos:
            return CompressionResult(
                groups=[],
                original_count=0,
                compressed_count=0,
                compression_ratio=0.0,
                merge_rules_hit={},
                chain_types_used=[]
            )
        
        original_count = len(todos)
        groups: List[TodoGroup] = []
        processed_ids: Set[str] = set()
        
        # Step 1: 同義語正規化（既にTodoItem.__post_init__で実行済み）
        self.merge_rules_hit["SYNONYM_NORMALIZED"] = len(todos)
        
        # Step 2: 相互参照解決
        if clauses:
            reference_groups = self._group_by_references(todos, clauses)
            for group in reference_groups:
                if len(group.members) > 1:
                    groups.append(group)
                    processed_ids.update(t.todo_id for t in group.members)
                    self.merge_rules_hit["CROSS_REFERENCE"] += len(group.members)
        
        # Step 3: 階層構造認識
        if clauses:
            hierarchy_groups = self._group_by_hierarchy(todos, clauses, processed_ids)
            for group in hierarchy_groups:
                groups.append(group)
                processed_ids.update(t.todo_id for t in group.members)
                self.merge_rules_hit["HIERARCHY"] += len(group.members)
        
        # Step 4: 連鎖パターンマッチング
        remaining = [t for t in todos if t.todo_id not in processed_ids]
        chain_groups = self._group_by_chains(remaining)
        for group in chain_groups:
            if len(group.members) > 1:
                groups.append(group)
                processed_ids.update(t.todo_id for t in group.members)
                self.merge_rules_hit["CHAIN_BUNDLED"] += len(group.members)
        
        # Step 5: 近接性グルーピング
        remaining = [t for t in todos if t.todo_id not in processed_ids]
        proximity_groups = self._group_by_proximity(remaining)
        for group in proximity_groups:
            if len(group.members) > 1:
                groups.append(group)
                processed_ids.update(t.todo_id for t in group.members)
                self.merge_rules_hit["PROXIMITY"] += len(group.members)
        
        # Step 6: ドメイン統合
        remaining = [t for t in todos if t.todo_id not in processed_ids]
        domain_groups = self._group_by_domain(remaining)
        for group in domain_groups:
            groups.append(group)
            processed_ids.update(t.todo_id for t in group.members)
            if len(group.members) > 1:
                self.merge_rules_hit["DOMAIN_MERGED"] += len(group.members)
        
        # Step 7: 残りを個別グループに
        remaining = [t for t in todos if t.todo_id not in processed_ids]
        for todo in remaining:
            group = TodoGroup(
                group_id=f"g_single_{todo.todo_id}",
                group_key=f"SINGLE_{todo.canonical_tags[0] if todo.canonical_tags else 'OTHER'}",
                group_reason="単独項目",
                canonical_domain=get_canonical_domain(todo.canonical_tags)
            )
            group.add_member(todo)
            groups.append(group)
        
        # Step 8: 最終マージ（同一ドメインのグループを統合）
        groups = self._final_merge(groups)
        
        # 結果計算
        compressed_count = len(groups)
        compression_ratio = 1.0 - (compressed_count / original_count) if original_count > 0 else 0.0
        
        chain_types_used = list(set(
            g.chain_type.value for g in groups if g.chain_type
        ))
        
        return CompressionResult(
            groups=groups,
            original_count=original_count,
            compressed_count=compressed_count,
            compression_ratio=compression_ratio,
            merge_rules_hit=dict(self.merge_rules_hit),
            chain_types_used=chain_types_used
        )
    
    def _group_by_references(self, todos: List[TodoItem], clauses: List[Dict]) -> List[TodoGroup]:
        """相互参照に基づくグルーピング"""
        groups = []
        
        # 参照を抽出
        references = extract_cross_references(clauses)
        if not references:
            return groups
        
        # 参照グラフを構築
        graph = build_reference_graph(references)
        all_clause_ids = [t.clause_id for t in todos]
        
        # 連結成分を発見
        components = find_connected_components(graph, all_clause_ids)
        
        # ToDo IDマッピング
        clause_to_todos = defaultdict(list)
        for todo in todos:
            clause_to_todos[todo.clause_id].append(todo)
        
        for i, component in enumerate(components):
            member_todos = []
            for clause_id in component:
                member_todos.extend(clause_to_todos.get(clause_id, []))
            
            if len(member_todos) > 1:
                tags = []
                for t in member_todos:
                    tags.extend(t.canonical_tags)
                
                group = TodoGroup(
                    group_id=f"g_ref_{i}",
                    group_key=f"REF_{get_canonical_domain(tags) or 'LINKED'}",
                    group_reason="相互参照で結ばれた条項群を一括確認",
                    canonical_domain=get_canonical_domain(tags),
                    merge_rules=["CROSS_REFERENCE"]
                )
                for todo in member_todos:
                    group.add_member(todo)
                groups.append(group)
        
        return groups
    
    def _group_by_hierarchy(self, todos: List[TodoItem], clauses: List[Dict], 
                           processed_ids: Set[str]) -> List[TodoGroup]:
        """階層構造に基づくグルーピング"""
        groups = []
        
        # 未処理のToDoに対応する条項のみ
        remaining_clause_ids = {t.clause_id for t in todos if t.todo_id not in processed_ids}
        filtered_clauses = [c for c in clauses if c.get("clause_id") in remaining_clause_ids]
        
        if not filtered_clauses:
            return groups
        
        # 階層検出
        hierarchy = detect_hierarchy(filtered_clauses)
        hierarchy_groups = group_by_hierarchy(hierarchy)
        
        # ToDo IDマッピング
        clause_to_todos = defaultdict(list)
        for todo in todos:
            if todo.todo_id not in processed_ids:
                clause_to_todos[todo.clause_id].append(todo)
        
        for i, component in enumerate(hierarchy_groups):
            member_todos = []
            for clause_id in component:
                member_todos.extend(clause_to_todos.get(clause_id, []))
            
            if len(member_todos) > 1:
                tags = []
                for t in member_todos:
                    tags.extend(t.canonical_tags)
                
                group = TodoGroup(
                    group_id=f"g_hier_{i}",
                    group_key=f"HIER_{get_canonical_domain(tags) or 'NESTED'}",
                    group_reason="階層構造（条・項・号）を一括確認",
                    canonical_domain=get_canonical_domain(tags),
                    merge_rules=["HIERARCHY"]
                )
                for todo in member_todos:
                    group.add_member(todo)
                groups.append(group)
        
        return groups
    
    def _group_by_chains(self, todos: List[TodoItem]) -> List[TodoGroup]:
        """連鎖パターンに基づくグルーピング（改良版）"""
        groups = []
        used_todo_ids = set()
        
        # パターンごとに候補を収集（優先度順）
        for pattern in sorted(self.chain_patterns, key=lambda p: -p.priority):
            candidates = []
            
            for todo in todos:
                if todo.todo_id in used_todo_ids:
                    continue
                    
                score = 0
                for keyword in pattern.keywords:
                    if keyword in todo.clause_text or keyword in todo.check_point:
                        score += 1
                
                # タグベースのスコアも追加
                for component in pattern.components:
                    if component in todo.canonical_tags:
                        score += 2
                
                if score >= pattern.min_components:
                    candidates.append((todo, score))
            
            if len(candidates) >= 2:
                # スコア順にソート
                candidates.sort(key=lambda x: -x[1])
                
                tags = []
                member_todos = []
                for t, _ in candidates:
                    tags.extend(t.canonical_tags)
                    member_todos.append(t)
                    used_todo_ids.add(t.todo_id)
                
                group = TodoGroup(
                    group_id=f"g_chain_{pattern.chain_type.name}_{len(groups)}",
                    group_key=f"CHAIN_{pattern.chain_type.name}",
                    group_reason=f"連鎖パターン「{pattern.chain_type.value}」を一括確認",
                    canonical_domain=get_canonical_domain(tags),
                    chain_type=pattern.chain_type,
                    merge_rules=["CHAIN_BUNDLED"]
                )
                
                for todo in member_todos:
                    group.add_member(todo)
                
                groups.append(group)
        
        return groups
    
    def _group_by_proximity(self, todos: List[TodoItem], max_distance: int = 5) -> List[TodoGroup]:
        """近接性に基づくグルーピング"""
        groups = []
        
        if not todos:
            return groups
        
        # clause_indexでソート
        sorted_todos = sorted(todos, key=lambda t: t.clause_index)
        
        current_group = []
        last_index = -100
        
        for todo in sorted_todos:
            if todo.clause_index - last_index <= max_distance:
                current_group.append(todo)
            else:
                if len(current_group) > 1:
                    tags = []
                    for t in current_group:
                        tags.extend(t.canonical_tags)
                    
                    group = TodoGroup(
                        group_id=f"g_prox_{len(groups)}",
                        group_key=f"PROX_{get_canonical_domain(tags) or 'ADJACENT'}",
                        group_reason="近接条項を一括確認",
                        canonical_domain=get_canonical_domain(tags),
                        merge_rules=["PROXIMITY"]
                    )
                    for t in current_group:
                        group.add_member(t)
                    groups.append(group)
                
                current_group = [todo]
            
            last_index = todo.clause_index
        
        # 最後のグループ
        if len(current_group) > 1:
            tags = []
            for t in current_group:
                tags.extend(t.canonical_tags)
            
            group = TodoGroup(
                group_id=f"g_prox_{len(groups)}",
                group_key=f"PROX_{get_canonical_domain(tags) or 'ADJACENT'}",
                group_reason="近接条項を一括確認",
                canonical_domain=get_canonical_domain(tags),
                merge_rules=["PROXIMITY"]
            )
            for t in current_group:
                group.add_member(t)
            groups.append(group)
        
        return groups
    
    def _group_by_domain(self, todos: List[TodoItem]) -> List[TodoGroup]:
        """ドメインに基づくグルーピング"""
        domain_map = defaultdict(list)
        
        for todo in todos:
            domain = get_canonical_domain(todo.canonical_tags) or "OTHER"
            domain_map[domain].append(todo)
        
        groups = []
        for domain, members in domain_map.items():
            group = TodoGroup(
                group_id=f"g_dom_{domain}",
                group_key=f"DOM_{domain}",
                group_reason=f"同一ドメイン「{domain}」を一括確認",
                canonical_domain=domain,
                merge_rules=["DOMAIN_MERGED"]
            )
            for todo in members:
                group.add_member(todo)
            groups.append(group)
        
        return groups
    
    def _final_merge(self, groups: List[TodoGroup]) -> List[TodoGroup]:
        """最終マージ（積極的にグループを統合して90%達成）"""
        if len(groups) <= 2:
            return groups
        
        # Phase 1: 同一ドメインのグループを強制統合
        domain_groups = defaultdict(list)
        for group in groups:
            domain = group.canonical_domain or "OTHER"
            domain_groups[domain].append(group)
        
        merged_phase1 = []
        for domain, domain_group_list in domain_groups.items():
            if len(domain_group_list) == 1:
                merged_phase1.append(domain_group_list[0])
            else:
                # 同一ドメインのグループを統合
                combined = TodoGroup(
                    group_id=f"g_merged_{domain}",
                    group_key=f"MERGED_{domain}",
                    group_reason=f"ドメイン「{domain}」の関連項目を統合確認",
                    canonical_domain=domain,
                    merge_rules=["FINAL_MERGE"]
                )
                for g in domain_group_list:
                    for member in g.members:
                        combined.add_member(member)
                    combined.merge_rules.extend(g.merge_rules)
                
                combined.merge_rules = list(set(combined.merge_rules))
                merged_phase1.append(combined)
        
        # Phase 2: 小グループ（3件以下）を近いドメインに吸収
        if len(merged_phase1) > 3:
            large_groups = [g for g in merged_phase1 if len(g.members) > 3]
            small_groups = [g for g in merged_phase1 if len(g.members) <= 3]
            
            if large_groups and small_groups:
                # 最大のグループに小グループを吸収
                largest = max(large_groups, key=lambda g: len(g.members))
                for small in small_groups:
                    for member in small.members:
                        largest.add_member(member)
                    largest.merge_rules.extend(small.merge_rules)
                
                largest.merge_rules = list(set(largest.merge_rules))
                largest.group_reason = "関連条項を一括確認（統合グループ）"
                
                return [g for g in large_groups]  # 小グループを除外
        
        # Phase 3: それでも多い場合は関連ドメインを統合
        if len(merged_phase1) > 3:
            # 関連ドメインマップ
            related_domains = {
                "LIABILITY": ["INDEMNITY", "TERMINATION"],
                "CONFIDENTIAL": ["IP", "COMPLIANCE"],
                "PAYMENT": ["TERMINATION"],
                "DISPUTE": ["COMPLIANCE"],
            }
            
            final_merged = []
            absorbed = set()
            
            for group in merged_phase1:
                if group.group_id in absorbed:
                    continue
                
                domain = group.canonical_domain
                related = related_domains.get(domain, [])
                
                # 関連ドメインのグループを探して統合
                for other in merged_phase1:
                    if other.group_id in absorbed or other.group_id == group.group_id:
                        continue
                    
                    if other.canonical_domain in related:
                        for member in other.members:
                            group.add_member(member)
                        group.merge_rules.append("RELATED_DOMAIN_MERGE")
                        absorbed.add(other.group_id)
                
                final_merged.append(group)
            
            return final_merged
        
        return merged_phase1


# =============================================================================
# エクスポート
# =============================================================================

compressor = AdvancedTodoCompressor()


def compress_todos(todos: List[TodoItem], clauses: List[Dict] = None) -> CompressionResult:
    """ToDo圧縮の簡易関数"""
    return compressor.compress(todos, clauses)


def get_compression_stats() -> Dict:
    """圧縮統計"""
    return {
        "version": AdvancedTodoCompressor.VERSION,
        "target_compression": AdvancedTodoCompressor.TARGET_COMPRESSION,
        "synonym_categories": len(SYNONYM_MAPS),
        "chain_patterns": len(CHAIN_PATTERNS),
        "total_synonyms": sum(len(v) for v in SYNONYM_MAPS.values()),
    }
