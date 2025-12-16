"""
VERITAS Domain Pack: IT/SaaS (IT・SaaSサービス契約)
Version: 1.58.0

対象: SaaS利用規約、ソフトウェアライセンス契約、SLA、クラウドサービス契約
主要法令: 電子消費者契約法、特定商取引法、消費者契約法、個人情報保護法

設計原則:
- FALSE_OK=0 の死守
- Core不変、知識分離
- ユーザー（利用者）保護の観点からの厳格判定
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ITSaaSVerdict(Enum):
    """IT/SaaS契約特有の判定結果"""
    NG_CRITICAL = "NG_CRITICAL"      # 法令違反・重大な不当条項
    NG = "NG"                         # 不当条項・無効リスク
    REVIEW_HIGH = "REVIEW_HIGH"       # 高リスク要確認
    REVIEW_MED = "REVIEW_MED"         # 中リスク要確認
    OK_CAUTION = "OK_CAUTION"         # 条件付きOK
    OK = "OK"                         # 問題なし


@dataclass
class ITSaaSCheckResult:
    """IT/SaaS契約チェック結果"""
    verdict: ITSaaSVerdict
    trigger_name: str
    matched_text: str
    check_points: List[str]
    legal_basis: str
    rewrite_suggestion: Optional[str] = None


# =============================================================================
# NG_CRITICAL: 法令違反・重大な不当条項
# =============================================================================

ITSAAS_NG_CRITICAL_TRIGGERS = {
    # 一方的サービス停止（事前通知なし）
    "unilateral_suspension_no_notice": {
        "pattern": r"(サービス|システム).{0,30}(いつでも|事前.{0,5}なく|通知.{0,5}なく|予告.{0,5}なく).{0,10}(停止|中止|終了)|(サービス|システム).{0,20}(停止|中止|終了).{0,20}(いつでも|事前.{0,5}なく|通知.{0,5}なく|予告.{0,5}なく)",
        "check_points": [
            "事前通知なしの一方的サービス停止",
            "消費者契約法10条で無効となる可能性",
            "契約目的を達成できなくなるリスク"
        ],
        "legal_basis": "消費者契約法10条、民法1条2項（信義則）",
        "rewrite": "「サービスの停止は、緊急の場合を除き、○日前までに通知する」"
    },
    
    # データ消去の事前通知なし
    "data_deletion_no_notice": {
        "pattern": r"(データ|情報|コンテンツ).{0,30}(通知.{0,5}なく|事前.{0,5}なく|いつでも).{0,10}(削除|消去|廃棄)|(データ|情報|コンテンツ).{0,20}(削除|消去|廃棄).{0,20}(いつでも|事前.{0,5}なく|通知.{0,5}なく)",
        "check_points": [
            "ユーザーデータの一方的削除条項",
            "重大な財産的損害を生じ得る",
            "個人情報保護法上の問題も"
        ],
        "legal_basis": "消費者契約法10条、個人情報保護法",
        "rewrite": "「解約後○日間はデータを保持し、その間にエクスポート可能とする」"
    },
    
    # 全面免責条項
    "total_liability_waiver": {
        "pattern": r"(いかなる|一切|すべて).{0,10}(損害|責任|賠償).{0,20}(負わない|免責|責任を負いません)",
        "check_points": [
            "事業者の責任を全面的に免除する条項",
            "消費者契約法8条で無効",
            "故意・重過失による損害は免責不可"
        ],
        "legal_basis": "消費者契約法8条1項1号・3号",
        "rewrite": "「当社の故意または重過失による損害を除き、賠償額は過去○ヶ月の利用料金を上限とする」"
    },
    
    # 規約変更の無制限
    "unlimited_tos_change": {
        "pattern": r"(規約|約款|条件).{0,30}(当社.{0,5}判断|いつでも|自由に).{0,10}(変更|改定|改正)|(規約|約款|条件).{0,20}(変更|改定|改正).{0,20}(いつでも|自由に|当社.{0,5}判断).{0,20}(できる|する)",
        "check_points": [
            "無制限の規約変更権限",
            "民法548条の4の要件を満たさない可能性",
            "変更通知・異議申立期間が必要"
        ],
        "legal_basis": "民法548条の4、消費者契約法10条",
        "rewrite": "「変更は○日前に通知し、異議がある場合は解約可能とする」"
    },
    
    # 個人情報の無断第三者提供
    "unauthorized_data_sharing": {
        "pattern": r"(個人情報|利用者情報|ユーザー.{0,5}情報).{0,20}(第三者|外部).{0,10}(提供|共有|開示).{0,10}(できる|する)",
        "check_points": [
            "同意なき個人情報の第三者提供",
            "個人情報保護法27条違反",
            "オプトアウト手続きの有無を確認"
        ],
        "legal_basis": "個人情報保護法27条",
        "rewrite": "「第三者提供は、利用者の事前同意を得た場合に限る」"
    },
    
    # 著作権の全面譲渡
    "forced_ip_transfer": {
        "pattern": r"(ユーザー|利用者).{0,10}(コンテンツ|著作物|成果物).{0,20}(著作権|知的財産権).{0,10}(譲渡|移転|帰属)",
        "check_points": [
            "ユーザーの著作物を強制的に譲渡させる条項",
            "対価なき権利移転は無効となり得る",
            "ライセンス許諾との混同に注意"
        ],
        "legal_basis": "著作権法61条、消費者契約法10条",
        "rewrite": "「ユーザーは、サービス提供に必要な範囲でコンテンツの利用を許諾する」"
    },
}


# =============================================================================
# NG: 不当条項・無効リスク
# =============================================================================

ITSAAS_NG_TRIGGERS = {
    # SLA未達時の救済なし
    "no_sla_remedy": {
        "pattern": r"(SLA|稼働率|可用性).{0,30}(未達|達成.{0,5}ない|満たさない).{0,20}(責任|補償|返金).{0,10}(ない|なし|しない)",
        "check_points": [
            "SLA未達時の救済措置がない",
            "サービス品質保証の実効性なし",
            "クレジット付与等の規定が必要"
        ],
        "legal_basis": "契約の本旨（民法415条）",
        "rewrite": "「SLA未達の場合、未達時間に応じたサービスクレジットを付与する」"
    },
    
    # 解約時データ返還拒否
    "no_data_return": {
        "pattern": r"(解約|終了|契約.{0,5}終了).{0,20}(データ|情報).{0,10}(返還|返却|エクスポート).{0,10}(しない|できない|不可)",
        "check_points": [
            "解約時のデータ返還を拒否する条項",
            "ユーザーデータへのアクセス権を侵害",
            "ロックイン戦略だが法的問題あり"
        ],
        "legal_basis": "民法1条2項（信義則）、GDPR20条参照",
        "rewrite": "「解約後○日間、データのエクスポートを可能とする」"
    },
    
    # 一方的な値上げ
    "unilateral_price_increase": {
        "pattern": r"(料金|価格|利用料).{0,30}(いつでも|通知.{0,5}のみ|一方的).{0,10}(変更|改定|値上げ)|(料金|価格|利用料).{0,20}(変更|改定|値上げ).{0,20}(いつでも|通知.{0,5}のみ|一方的)",
        "check_points": [
            "一方的な価格変更条項",
            "消費者契約法10条で無効の可能性",
            "値上げ時の解約権保障が必要"
        ],
        "legal_basis": "消費者契約法10条",
        "rewrite": "「料金改定は○日前に通知し、改定後料金に同意しない場合は解約可能とする」"
    },
    
    # 自動更新の解約困難
    "difficult_auto_renewal_cancel": {
        "pattern": r"(自動更新|自動継続).{0,30}(解約|解除).{0,20}(\d+)\s*(日|ヶ月).{0,5}(前|以前)",
        "check_points": [
            "自動更新の解約予告期間を確認",
            "30日超は消費者に不利な可能性",
            "特商法の表示義務を確認"
        ],
        "legal_basis": "特定商取引法15条の3",
        "validate": lambda m: int(m.group(3)) > 30 if "日" in m.group(4) else int(m.group(3)) > 1
    },
    
    # 競合サービス利用禁止
    "ban_competitor_use": {
        "pattern": r"(競合|類似|同種).{0,10}(サービス|製品).{0,10}(利用|使用).{0,10}(禁止|できない|してはならない)",
        "check_points": [
            "競合サービス利用禁止条項",
            "独占禁止法上の問題あり得る",
            "営業の自由を過度に制限"
        ],
        "legal_basis": "独占禁止法19条（不公正な取引方法）",
        "rewrite": "削除を推奨"
    },
    
    # 知的財産権侵害の全責任転嫁
    "ip_indemnity_user": {
        "pattern": r"(知的財産|特許|著作権).{0,20}(侵害|クレーム).{0,20}(ユーザー|利用者|乙).{0,10}(責任|負担|補償)",
        "check_points": [
            "サービス自体のIP侵害リスクをユーザーに転嫁",
            "提供者が負うべきリスクの不当転嫁",
            "ユーザーコンテンツのIP責任とは区別すべき"
        ],
        "legal_basis": "消費者契約法10条",
        "rewrite": "「サービス自体の知的財産権侵害については、当社が責任を負う」"
    },
}


# =============================================================================
# REVIEW_HIGH: 高リスク要確認
# =============================================================================

ITSAAS_REVIEW_HIGH_TRIGGERS = {
    # 利用規約変更通知
    "tos_change_notice": {
        "pattern": r"(規約|約款).{0,10}(変更|改定).{0,20}(通知|お知らせ|告知).{0,20}(\d+)\s*(日|週間)",
        "check_points": [
            "規約変更の事前通知期間を確認",
            "7日未満は短すぎる可能性",
            "重要変更は個別通知が望ましい"
        ],
        "legal_basis": "民法548条の4"
    },
    
    # 稼働率保証
    "sla_uptime": {
        "pattern": r"(稼働率|可用性|アップタイム).{0,20}(\d+\.?\d*)\s*(%|パーセント)",
        "check_points": [
            "SLAの稼働率保証を確認",
            "99.9%（月間約43分停止許容）が標準的",
            "計算方法（計画停止除外等）を確認"
        ],
        "legal_basis": "契約条件"
    },
    
    # データ保持期間
    "data_retention": {
        "pattern": r"(データ|ログ|情報).{0,10}(保持|保存|保管).{0,20}(\d+)\s*(日|ヶ月|年)",
        "check_points": [
            "データ保持期間の妥当性を確認",
            "法定保存義務との整合性",
            "解約後の保持期間も確認"
        ],
        "legal_basis": "個人情報保護法、各業法"
    },
    
    # セキュリティ基準
    "security_standard": {
        "pattern": r"(セキュリティ|安全管理).{0,30}(措置|対策|基準).{0,10}(講じる|実施)",
        "check_points": [
            "具体的なセキュリティ基準を確認",
            "ISO27001、SOC2等の認証有無",
            "インシデント発生時の通知義務"
        ],
        "legal_basis": "個人情報保護法23条"
    },
    
    # 損害賠償上限
    "liability_cap": {
        "pattern": r"(損害賠償|賠償).{0,10}(上限|限度|Cap).{0,20}(\d+)\s*(ヶ月|箇月|年)",
        "check_points": [
            "賠償上限の妥当性を確認",
            "過去12ヶ月の利用料が標準的",
            "故意・重過失は上限適用外か確認"
        ],
        "legal_basis": "消費者契約法8条"
    },
    
    # API利用制限
    "api_rate_limit": {
        "pattern": r"(API|インターフェース).{0,20}(制限|リミット|上限).{0,20}(超過|超える).{0,10}(停止|制限)",
        "check_points": [
            "API利用制限と超過時の対応を確認",
            "事前通知の有無",
            "追加料金の発生有無"
        ],
        "legal_basis": "契約条件"
    },
}


# =============================================================================
# REVIEW_MED: 中リスク要確認
# =============================================================================

ITSAAS_REVIEW_MED_TRIGGERS = {
    # サポート範囲
    "support_scope": {
        "pattern": r"(サポート|カスタマーサポート|問い合わせ).{0,20}(範囲|対象|時間|受付)",
        "check_points": [
            "サポート範囲と対応時間を確認",
            "追加サポートの料金体系",
            "SLAとの整合性"
        ],
        "legal_basis": "契約条件"
    },
    
    # アップデート・メンテナンス
    "maintenance_notice": {
        "pattern": r"(メンテナンス|アップデート|更新).{0,20}(通知|予告|お知らせ).{0,20}(\d+)\s*(日|時間)",
        "check_points": [
            "メンテナンス事前通知期間を確認",
            "緊急メンテナンスの定義",
            "SLAへの影響の取扱い"
        ],
        "legal_basis": "契約条件"
    },
    
    # 第三者サービス連携
    "third_party_integration": {
        "pattern": r"(第三者|外部|サードパーティ).{0,10}(サービス|API|連携).{0,20}(責任|保証)",
        "check_points": [
            "第三者サービスの障害時の責任分担",
            "連携先の変更・終了時の対応",
            "データ連携時のセキュリティ"
        ],
        "legal_basis": "契約条件"
    },
    
    # バックアップ責任
    "backup_responsibility": {
        "pattern": r"(バックアップ|データ保全).{0,20}(ユーザー|利用者|お客様).{0,10}(責任|義務)",
        "check_points": [
            "バックアップ責任の所在を確認",
            "提供者側のバックアップ体制",
            "復旧SLAの有無"
        ],
        "legal_basis": "契約条件"
    },
}


# =============================================================================
# OK_CAUTION: 条件付きOK（標準的なIT/SaaS条項）
# =============================================================================

ITSAAS_OK_CAUTION_PATTERNS = {
    "reasonable_liability_cap": {
        "pattern": r"(賠償|責任).{0,10}(上限|限度).{0,20}(12|１２|12ヶ月|1年|過去.{0,5}年).{0,10}(利用料|料金)",
        "check_points": [
            "過去12ヶ月の利用料を上限とする標準的な条項",
            "故意・重過失の除外を確認"
        ],
        "legal_basis": "業界標準"
    },
    
    "reasonable_tos_change": {
        "pattern": r"(規約|約款).{0,10}(変更|改定).{0,20}(30|３０|30日|1ヶ月).{0,10}(前|以前).{0,10}(通知|告知)",
        "check_points": [
            "30日前通知は標準的",
            "重要変更の個別通知を確認"
        ],
        "legal_basis": "民法548条の4"
    },
    
    "reasonable_data_export": {
        "pattern": r"(解約|終了).{0,20}(データ|情報).{0,10}(エクスポート|ダウンロード|取得).{0,10}(できる|可能)",
        "check_points": [
            "解約時のデータエクスポートを認める規定",
            "期間と形式を確認"
        ],
        "legal_basis": "信義則"
    },
    
    "reasonable_sla": {
        "pattern": r"(稼働率|可用性).{0,10}(99\.9|99\.5|99\.0)\s*%",
        "check_points": [
            "標準的なSLA水準",
            "未達時のクレジットを確認"
        ],
        "legal_basis": "業界標準"
    },
}


# =============================================================================
# メインエンジン
# =============================================================================

class ITSaaSPack:
    """IT/SaaSサービス契約ドメインパック"""
    
    VERSION = "1.58.0"
    DOMAIN = "IT_SAAS"
    
    def __init__(self):
        self.ng_critical = ITSAAS_NG_CRITICAL_TRIGGERS
        self.ng = ITSAAS_NG_TRIGGERS
        self.review_high = ITSAAS_REVIEW_HIGH_TRIGGERS
        self.review_med = ITSAAS_REVIEW_MED_TRIGGERS
        self.ok_caution = ITSAAS_OK_CAUTION_PATTERNS
    
    def analyze(self, clause_text: str) -> List[ITSaaSCheckResult]:
        """条項を分析し、IT/SaaSリスクを検出"""
        results = []
        
        # NG_CRITICAL チェック
        for name, trigger in self.ng_critical.items():
            match = re.search(trigger["pattern"], clause_text)
            if match:
                results.append(ITSaaSCheckResult(
                    verdict=ITSaaSVerdict.NG_CRITICAL,
                    trigger_name=name,
                    matched_text=match.group(0),
                    check_points=trigger["check_points"],
                    legal_basis=trigger["legal_basis"],
                    rewrite_suggestion=trigger.get("rewrite")
                ))
        
        # NG チェック
        for name, trigger in self.ng.items():
            match = re.search(trigger["pattern"], clause_text)
            if match:
                if "validate" in trigger:
                    if not trigger["validate"](match):
                        continue
                results.append(ITSaaSCheckResult(
                    verdict=ITSaaSVerdict.NG,
                    trigger_name=name,
                    matched_text=match.group(0),
                    check_points=trigger["check_points"],
                    legal_basis=trigger["legal_basis"],
                    rewrite_suggestion=trigger.get("rewrite")
                ))
        
        # REVIEW_HIGH チェック
        for name, trigger in self.review_high.items():
            match = re.search(trigger["pattern"], clause_text)
            if match:
                results.append(ITSaaSCheckResult(
                    verdict=ITSaaSVerdict.REVIEW_HIGH,
                    trigger_name=name,
                    matched_text=match.group(0),
                    check_points=trigger["check_points"],
                    legal_basis=trigger["legal_basis"]
                ))
        
        # REVIEW_MED チェック
        for name, trigger in self.review_med.items():
            match = re.search(trigger["pattern"], clause_text)
            if match:
                results.append(ITSaaSCheckResult(
                    verdict=ITSaaSVerdict.REVIEW_MED,
                    trigger_name=name,
                    matched_text=match.group(0),
                    check_points=trigger["check_points"],
                    legal_basis=trigger["legal_basis"]
                ))
        
        # OK_CAUTION チェック
        if not any(r.verdict in [ITSaaSVerdict.NG_CRITICAL, ITSaaSVerdict.NG] for r in results):
            for name, pattern_info in self.ok_caution.items():
                match = re.search(pattern_info["pattern"], clause_text)
                if match:
                    results.append(ITSaaSCheckResult(
                        verdict=ITSaaSVerdict.OK_CAUTION,
                        trigger_name=name,
                        matched_text=match.group(0),
                        check_points=pattern_info["check_points"],
                        legal_basis=pattern_info["legal_basis"]
                    ))
        
        return results
    
    def get_worst_verdict(self, results: List[ITSaaSCheckResult]) -> ITSaaSVerdict:
        """最も厳しい判定を返す"""
        if not results:
            return ITSaaSVerdict.OK
        
        priority = [
            ITSaaSVerdict.NG_CRITICAL,
            ITSaaSVerdict.NG,
            ITSaaSVerdict.REVIEW_HIGH,
            ITSaaSVerdict.REVIEW_MED,
            ITSaaSVerdict.OK_CAUTION,
            ITSaaSVerdict.OK
        ]
        
        for verdict in priority:
            if any(r.verdict == verdict for r in results):
                return verdict
        
        return ITSaaSVerdict.OK
    
    def get_statistics(self) -> Dict:
        """パック統計情報"""
        return {
            "domain": self.DOMAIN,
            "version": self.VERSION,
            "ng_critical_count": len(self.ng_critical),
            "ng_count": len(self.ng),
            "review_high_count": len(self.review_high),
            "review_med_count": len(self.review_med),
            "ok_caution_count": len(self.ok_caution),
            "total_triggers": (
                len(self.ng_critical) + len(self.ng) + 
                len(self.review_high) + len(self.review_med) +
                len(self.ok_caution)
            ),
            "patent_map": ["CLAIM_1", "CLAIM_2", "CLAIM_3", "CLAIM_4", "CLAIM_5"]
        }


# エクスポート
it_saas_pack = ITSaaSPack()
