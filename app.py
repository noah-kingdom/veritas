#!/usr/bin/env python3
"""
VERITAS - AI契約書レビューエンジン
===================================
Streamlit Cloud デプロイ版

Patent: 2025-159636
「嘘なく、誇張なく、過不足なく」
"""

import streamlit as st
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import json

# =============================================================================
# ページ設定
# =============================================================================

st.set_page_config(
    page_title="VERITAS - AI契約書レビュー",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# データクラス定義
# =============================================================================

class RiskLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SAFE = "SAFE"

@dataclass
class Issue:
    issue_id: str
    clause_text: str
    issue_type: str
    risk_level: RiskLevel
    description: str
    legal_basis: str
    fix_suggestion: str

# =============================================================================
# 危険パターン定義（101パターンから主要なものを抽出）
# =============================================================================

DANGER_PATTERNS = [
    # 完全免責系
    {
        "id": "CRT001",
        "pattern": r"(一切|いかなる|全て).{0,10}(責任|賠償|補償).{0,10}(負わない|しない|免除|免責)",
        "type": "完全免責条項",
        "risk": RiskLevel.CRITICAL,
        "description": "事業者の責任を全面的に免除する条項は、消費者契約法第8条により無効となる可能性があります。",
        "legal_basis": "消費者契約法第8条（事業者の損害賠償責任を免除する条項の無効）",
        "fix": "「当社の故意または重大な過失による場合を除き」等の限定を追加してください。"
    },
    {
        "id": "CRT002",
        "pattern": r"(法令|法律|裁判所).{0,10}(開示|提出|報告).{0,10}(禁止|できない|してはならない)",
        "type": "法令開示禁止",
        "risk": RiskLevel.CRITICAL,
        "description": "法令により義務付けられた開示を禁止する条項は履行不能であり、法的に無効です。",
        "legal_basis": "刑事訴訟法、各種業法の開示義務規定",
        "fix": "「法令により開示が義務付けられる場合を除く」を追加してください。"
    },
    # 高リスク系
    {
        "id": "HIG001",
        "pattern": r"(いつでも|任意|自由).{0,5}(解除|解約|終了).{0,10}(できる|可能)",
        "type": "一方的解除権",
        "risk": RiskLevel.HIGH,
        "description": "一方当事者のみに無条件の解除権を認める条項は、契約の安定性を著しく損なう可能性があります。",
        "legal_basis": "民法第1条第2項（信義則）",
        "fix": "解除事由を限定するか、双方に同等の権利を付与してください。"
    },
    {
        "id": "HIG002",
        "pattern": r"(検収|検査|受入).{0,10}(拒否|拒絶).{0,10}(理由|事由).{0,5}(なく|問わず|不要)",
        "type": "検収拒否無制限",
        "risk": RiskLevel.HIGH,
        "description": "理由なく検収を拒否できる条項は、下請法に違反する可能性があります。",
        "legal_basis": "下請法第4条第1項第1号（受領拒否の禁止）",
        "fix": "検収拒否の理由明示と、異議申立て期間を設定してください。"
    },
    {
        "id": "HIG003",
        "pattern": r"(違約金|損害賠償).{0,10}(上限|制限).{0,5}(なし|ない|設けない)",
        "type": "違約金上限なし",
        "risk": RiskLevel.HIGH,
        "description": "違約金の上限がない条項は、過大な負担を強いる可能性があります。",
        "legal_basis": "民法第420条（賠償額の予定）、民法第90条（公序良俗）",
        "fix": "契約金額の一定割合を上限として設定してください。"
    },
    {
        "id": "HIG004",
        "pattern": r"(競業|競合|同業).{0,10}(禁止|避止|制限).{0,10}(無期限|永久|期間.{0,5}(なし|ない))",
        "type": "競業避止無期限",
        "risk": RiskLevel.HIGH,
        "description": "無期限の競業避止義務は、職業選択の自由を過度に制限し無効となる可能性があります。",
        "legal_basis": "憲法第22条（職業選択の自由）、判例",
        "fix": "期間・地域・業種を合理的な範囲に限定してください。"
    },
    # 中リスク系
    {
        "id": "MED001",
        "pattern": r"(知的財産|著作権|特許).{0,10}(全て|一切|すべて).{0,10}(帰属|譲渡|移転)",
        "type": "知財全面譲渡",
        "risk": RiskLevel.MEDIUM,
        "description": "知的財産権を無条件で全面譲渡する条項は、対価の妥当性を確認する必要があります。",
        "legal_basis": "著作権法第27条、第28条",
        "fix": "譲渡範囲を明確化し、適正な対価を設定してください。"
    },
    {
        "id": "MED002",
        "pattern": r"(準拠法|管轄).{0,10}(外国|海外|[A-Z]{2,})",
        "type": "外国法準拠",
        "risk": RiskLevel.MEDIUM,
        "description": "外国法を準拠法とする場合、紛争解決コストが増大する可能性があります。",
        "legal_basis": "法の適用に関する通則法",
        "fix": "日本法を準拠法とすることを検討してください。"
    },
    {
        "id": "MED003",
        "pattern": r"(自動更新|自動延長).{0,10}(申し出.{0,5}ない限り|通知.{0,5}ない場合)",
        "type": "自動更新条項",
        "risk": RiskLevel.MEDIUM,
        "description": "自動更新条項は、解約を忘れると契約が継続するリスクがあります。",
        "legal_basis": "消費者契約法（情報提供義務）",
        "fix": "更新前に通知する仕組みを設けてください。"
    },
    # 労働法関連
    {
        "id": "LAB001",
        "pattern": r"(残業|時間外).{0,10}(上限.{0,5}(なし|ない)|無制限)",
        "type": "残業上限なし",
        "risk": RiskLevel.CRITICAL,
        "description": "残業時間の上限がない条項は、労働基準法に違反します。",
        "legal_basis": "労働基準法第36条（時間外労働の上限規制）",
        "fix": "月45時間、年360時間の上限を明記してください。"
    },
    {
        "id": "LAB002",
        "pattern": r"(有給|年休|休暇).{0,10}(取得.{0,5}(できない|禁止)|買い取り.{0,5}強制)",
        "type": "有給取得制限",
        "risk": RiskLevel.CRITICAL,
        "description": "有給休暇の取得を制限する条項は、労働基準法に違反します。",
        "legal_basis": "労働基準法第39条（年次有給休暇）",
        "fix": "有給休暇の取得を保障する条項に修正してください。"
    },
    # 下請法関連
    {
        "id": "SUB001",
        "pattern": r"(支払|代金).{0,10}(60日|2.?ヶ?月).{0,5}(超|以上|を超え)",
        "type": "支払遅延",
        "risk": RiskLevel.HIGH,
        "description": "60日を超える支払いサイトは、下請法に違反する可能性があります。",
        "legal_basis": "下請法第2条の2（下請代金の支払期日）",
        "fix": "支払期日を納品後60日以内に設定してください。"
    },
    {
        "id": "SUB002",
        "pattern": r"(単価|価格|対価).{0,10}(一方的|協議.{0,5}なく).{0,10}(変更|減額|引下げ)",
        "type": "一方的減額",
        "risk": RiskLevel.CRITICAL,
        "description": "一方的な単価引き下げは、下請法の禁止行為に該当します。",
        "legal_basis": "下請法第4条第1項第3号（下請代金の減額の禁止）",
        "fix": "価格変更には双方の合意が必要であることを明記してください。"
    },
]

# =============================================================================
# VERITAS エンジン（簡易版）
# =============================================================================

class VeritasEngine:
    """VERITAS 契約書分析エンジン"""
    
    def __init__(self):
        self.patterns = DANGER_PATTERNS
    
    def analyze(self, text: str) -> List[Issue]:
        """契約書テキストを分析"""
        issues = []
        
        for pattern_def in self.patterns:
            matches = re.finditer(pattern_def["pattern"], text, re.IGNORECASE)
            
            for match in matches:
                # 前後のコンテキストを取得
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                issue = Issue(
                    issue_id=pattern_def["id"],
                    clause_text=context,
                    issue_type=pattern_def["type"],
                    risk_level=pattern_def["risk"],
                    description=pattern_def["description"],
                    legal_basis=pattern_def["legal_basis"],
                    fix_suggestion=pattern_def["fix"]
                )
                issues.append(issue)
        
        return issues
    
    def get_risk_summary(self, issues: List[Issue]) -> Dict[str, int]:
        """リスクレベル別の集計"""
        summary = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        }
        
        for issue in issues:
            if issue.risk_level.value in summary:
                summary[issue.risk_level.value] += 1
        
        return summary

# =============================================================================
# UI コンポーネント
# =============================================================================

def render_header():
    """ヘッダー表示"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); 
                padding: 2rem; border-radius: 12px; color: white; margin-bottom: 2rem;">
        <h1 style="margin: 0; font-size: 2.5rem;">🔍 VERITAS</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.1rem;">
            AI契約書レビューエンジン ― 嘘なく、誇張なく、過不足なく
        </p>
        <p style="margin: 0.3rem 0 0 0; opacity: 0.7; font-size: 0.9rem;">
            Patent: 2025-159636
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_risk_badge(risk: RiskLevel) -> str:
    """リスクレベルバッジ"""
    colors = {
        RiskLevel.CRITICAL: ("#dc2626", "⛔"),
        RiskLevel.HIGH: ("#ea580c", "🔴"),
        RiskLevel.MEDIUM: ("#ca8a04", "🟡"),
        RiskLevel.LOW: ("#2563eb", "🔵"),
        RiskLevel.SAFE: ("#22c55e", "✅"),
    }
    color, icon = colors.get(risk, ("#666", "ℹ️"))
    return f"{icon} **{risk.value}**"

def render_issue_card(issue: Issue, index: int):
    """Issue カード表示"""
    risk_colors = {
        RiskLevel.CRITICAL: "#fef2f2",
        RiskLevel.HIGH: "#fff7ed",
        RiskLevel.MEDIUM: "#fefce8",
        RiskLevel.LOW: "#eff6ff",
    }
    border_colors = {
        RiskLevel.CRITICAL: "#dc2626",
        RiskLevel.HIGH: "#ea580c",
        RiskLevel.MEDIUM: "#ca8a04",
        RiskLevel.LOW: "#2563eb",
    }
    
    bg_color = risk_colors.get(issue.risk_level, "#f9fafb")
    border_color = border_colors.get(issue.risk_level, "#666")
    
    with st.container():
        st.markdown(f"""
        <div style="background: {bg_color}; padding: 1rem; border-radius: 8px; 
                    border-left: 4px solid {border_color}; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold;">#{index+1} {issue.issue_type}</span>
                <span>{render_risk_badge(issue.risk_level)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("詳細を見る", expanded=False):
            st.markdown("**該当箇所:**")
            st.code(issue.clause_text, language=None)
            
            st.markdown("**問題点:**")
            st.info(issue.description)
            
            st.markdown("**法的根拠:**")
            st.warning(issue.legal_basis)
            
            st.markdown("**修正提案:**")
            st.success(issue.fix_suggestion)

def render_summary(summary: Dict[str, int], total_issues: int):
    """サマリー表示"""
    cols = st.columns(4)
    
    metrics = [
        ("⛔ CRITICAL", summary["CRITICAL"], "#dc2626"),
        ("🔴 HIGH", summary["HIGH"], "#ea580c"),
        ("🟡 MEDIUM", summary["MEDIUM"], "#ca8a04"),
        ("🔵 LOW", summary["LOW"], "#2563eb"),
    ]
    
    for col, (label, count, color) in zip(cols, metrics):
        with col:
            st.metric(label, count)

# =============================================================================
# メインアプリ
# =============================================================================

def main():
    render_header()
    
    # サイドバー
    with st.sidebar:
        st.markdown("### ⚙️ 設定")
        
        analysis_mode = st.selectbox(
            "分析モード",
            ["標準分析", "詳細分析", "クイックスキャン"]
        )
        
        st.markdown("---")
        
        st.markdown("### 📊 検出パターン")
        st.info(f"**{len(DANGER_PATTERNS)}** パターン登録済み")
        
        st.markdown("---")
        
        st.markdown("### ℹ️ About")
        st.markdown("""
        **VERITAS**は、契約書の危険条項を
        自動検出するAIエンジンです。
        
        - 消費者契約法
        - 下請法
        - 労働基準法
        
        等の法令違反を検出します。
        """)
    
    # メインコンテンツ
    st.markdown("### 📄 契約書を入力")
    
    input_method = st.radio(
        "入力方法",
        ["テキスト入力", "サンプルを使用"],
        horizontal=True
    )
    
    if input_method == "サンプルを使用":
        sample_text = """
第5条（免責）
当社は、本サービスの利用により生じた一切の損害について、いかなる場合も責任を負わないものとします。

第8条（秘密保持）
乙は、本契約に関連して知り得た甲の秘密情報を、法令により開示が義務付けられる場合であっても、第三者に開示してはならない。

第12条（解除）
甲は、いつでも任意に本契約を解除することができる。この場合、甲は乙に対して何らの補償も行わないものとする。

第15条（支払条件）
甲は、乙から請求書を受領した日から90日以内に代金を支払うものとする。

第18条（競業避止）
乙は、本契約終了後も無期限に、甲と競合する事業を行ってはならない。

第20条（知的財産）
本契約に基づき乙が作成した成果物に関する知的財産権は、全て甲に帰属するものとする。
        """
        contract_text = st.text_area(
            "契約書テキスト",
            value=sample_text,
            height=400
        )
    else:
        contract_text = st.text_area(
            "契約書テキスト",
            placeholder="契約書のテキストを貼り付けてください...",
            height=400
        )
    
    # 分析実行
    if st.button("🔍 分析を実行", type="primary", use_container_width=True):
        if not contract_text.strip():
            st.error("契約書テキストを入力してください。")
            return
        
        with st.spinner("分析中..."):
            engine = VeritasEngine()
            issues = engine.analyze(contract_text)
            summary = engine.get_risk_summary(issues)
        
        st.markdown("---")
        
        # 結果表示
        if issues:
            st.markdown(f"### ⚠️ {len(issues)} 件の問題を検出")
            
            render_summary(summary, len(issues))
            
            st.markdown("---")
            
            # フィルタ
            risk_filter = st.multiselect(
                "リスクレベルでフィルタ",
                ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                default=["CRITICAL", "HIGH"]
            )
            
            filtered_issues = [
                issue for issue in issues 
                if issue.risk_level.value in risk_filter
            ]
            
            st.markdown(f"### 📋 検出された問題 ({len(filtered_issues)}件)")
            
            for i, issue in enumerate(filtered_issues):
                render_issue_card(issue, i)
        
        else:
            st.success("✅ 危険な条項は検出されませんでした。")
            st.balloons()
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>VERITAS v1.15 | Patent: 2025-159636 | 「嘘なく、誇張なく、過不足なく」</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
