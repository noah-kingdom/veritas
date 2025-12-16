"""
VERITAS v159 - Industry Whitelist Patterns
業界別ホワイトリストモジュール

目的: 誤検知（False Positive）削減
- 法令準拠を明示した条項
- 業界標準・ガイドライン準拠条項
- 判例で有効と認められたパターン

設計原則:
- FALSE_OK=0 維持（危険な条項を見逃さない）
- REVIEW率削減（安全な条項を無駄にREVIEWしない）
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class WhitelistVerdict(Enum):
    """ホワイトリスト判定結果"""
    OK_SAFE = "OK_SAFE"           # 明確に安全
    OK_STANDARD = "OK_STANDARD"   # 業界標準
    OK_COMPLIANT = "OK_COMPLIANT" # 法令準拠明示
    OK_CAUTION = "OK_CAUTION"     # 条件付きOK


@dataclass
class WhitelistResult:
    """ホワイトリスト検出結果"""
    verdict: WhitelistVerdict
    pattern_name: str
    matched_text: str
    reason: str
    applicable_domain: str
    legal_basis: str


# =============================================================================
# 労働契約 ホワイトリスト
# =============================================================================

LABOR_WHITELIST = {
    # 法令準拠明示
    "civil_code_627_resignation": {
        "pattern": r"(民法.{0,5}(627|六百二十七)|民法の規定).{0,10}(に基づき|に従い|により).{0,10}(退職|辞職)",
        "verdict": WhitelistVerdict.OK_SAFE,
        "reason": "民法627条に基づく退職権を明示的に認める条項",
        "legal_basis": "民法627条"
    },
    
    "labor_standards_36_agreement": {
        "pattern": r"(36協定|三六協定|時間外・休日労働に関する協定).{0,10}(範囲内|に基づき|に従い).{0,10}(時間外|残業|休日労働)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "36協定に基づく時間外労働の規定。法定要件を満たす",
        "legal_basis": "労働基準法36条"
    },
    
    "proper_dismissal_procedure": {
        "pattern": r"(解雇|雇止め).{0,20}(労働基準法|労基法).{0,10}(20条|二十条).{0,10}(に基づき|に従い|の規定により)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "労働基準法20条の解雇予告規定を遵守",
        "legal_basis": "労働基準法20条"
    },
    
    "annual_leave_legal_minimum": {
        "pattern": r"(年次有給休暇|有給休暇|年休).{0,20}(労働基準法|労基法).{0,10}(39条|三十九条).{0,10}(に基づき|に従い|の規定により)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "労働基準法39条の年次有給休暇規定を遵守",
        "legal_basis": "労働基準法39条"
    },
    
    "reasonable_noncompete": {
        "pattern": r"(競業避止|競業禁止).{0,30}(1年|一年|12ヶ月|12か月).{0,10}(以内|を超えない|間).{0,20}(代償措置|補償|手当)",
        "verdict": WhitelistVerdict.OK_CAUTION,
        "reason": "期間制限と代償措置を伴う合理的な競業避止条項",
        "legal_basis": "判例法理（競業避止義務の有効要件）"
    },
    
    "overtime_premium_legal": {
        "pattern": r"(時間外労働|残業).{0,15}(25|二十五).{0,5}(%|パーセント|割増).{0,20}(休日労働).{0,15}(35|三十五).{0,5}(%|パーセント|割増)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "法定の割増賃金率を満たす",
        "legal_basis": "労働基準法37条"
    },
    
    "subcontractor_protection": {
        "pattern": r"(下請法|下請代金支払遅延等防止法).{0,10}(に基づき|に従い|を遵守).{0,20}(支払|代金)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "下請法遵守を明示した条項",
        "legal_basis": "下請代金支払遅延等防止法"
    },
}


# =============================================================================
# 不動産契約 ホワイトリスト
# =============================================================================

REALESTATE_WHITELIST = {
    # 借地借家法準拠
    "land_lease_law_renewal": {
        "pattern": r"(借地借家法|借家法).{0,10}(に基づき|に従い|の規定により).{0,10}(更新|契約更新)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "借地借家法に基づく更新規定。借主保護が適用される",
        "legal_basis": "借地借家法26条"
    },
    
    "mlit_restoration_guideline": {
        "pattern": r"(国土交通省|国交省).{0,10}(ガイドライン|指針).{0,10}(に基づき|に従い|に準拠).{0,10}(原状回復|現状回復)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "国土交通省ガイドラインに準拠した原状回復基準",
        "legal_basis": "原状回復をめぐるトラブルとガイドライン（国土交通省）"
    },
    
    "proper_security_deposit": {
        "pattern": r"(敷金|保証金).{0,15}(賃料|家賃).{0,5}(の|×|かける).{0,5}([1-3]|[１-３]|一|二|三).{0,5}(ヶ月|か月|箇月).{0,10}(返還|精算)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "標準的な敷金額（1〜3ヶ月）で返還規定あり",
        "legal_basis": "民法622条の2"
    },
    
    "fixed_term_lease_proper": {
        "pattern": r"(定期借家|定期建物賃貸借).{0,10}(借地借家法|法).{0,10}(38条|三十八条).{0,10}(に基づき|に従い)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "借地借家法38条に基づく適法な定期借家契約",
        "legal_basis": "借地借家法38条"
    },
    
    "building_lots_and_buildings": {
        "pattern": r"(宅地建物取引業法|宅建業法).{0,10}(に基づき|に従い|を遵守).{0,20}(重要事項説明|37条書面)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "宅建業法の手続きを遵守",
        "legal_basis": "宅地建物取引業法35条・37条"
    },
    
    "reasonable_rent_revision": {
        "pattern": r"(賃料|家賃).{0,10}(改定|改訂|変更).{0,20}(借地借家法|法).{0,10}(32条|三十二条).{0,10}(に基づき|に従い|による協議)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "借地借家法32条に基づく賃料改定手続き",
        "legal_basis": "借地借家法32条"
    },
}


# =============================================================================
# IT/SaaS契約 ホワイトリスト
# =============================================================================

ITSAAS_WHITELIST = {
    # データ保護法準拠
    "gdpr_pipa_compliant": {
        "pattern": r"(GDPR|個人情報保護法|PIPA).{0,10}(に準拠|を遵守|に基づき|に従い).{0,10}(取り扱|管理|処理)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "個人情報保護法/GDPRへの準拠を明示",
        "legal_basis": "個人情報保護法、GDPR"
    },
    
    "iso27001_certified": {
        "pattern": r"(ISO.?27001|ISMS|情報セキュリティマネジメント).{0,10}(認証|取得|準拠).{0,10}(環境|体制|の下)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "ISO27001認証取得環境でのサービス提供",
        "legal_basis": "業界標準（ISO/IEC 27001）"
    },
    
    "soc2_compliant": {
        "pattern": r"(SOC.?2|SOC2).{0,10}(Type.?[12I]|タイプ[12１２]).{0,10}(報告書|認証|取得|準拠)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "SOC2認証に基づくセキュリティ体制",
        "legal_basis": "業界標準（AICPA SOC2）"
    },
    
    "reasonable_sla_with_credit": {
        "pattern": r"(稼働率|可用性).{0,10}(99\.9|99\.5).{0,5}%.{0,20}(未達|達成.{0,5}ない).{0,20}(クレジット|返金|補償)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "標準的SLA水準（99.5%以上）と未達時の救済措置あり",
        "legal_basis": "業界標準"
    },
    
    "data_export_guaranteed": {
        "pattern": r"(解約|終了|契約.{0,5}終了).{0,20}(データ|情報).{0,10}(エクスポート|ダウンロード|取得).{0,10}(30|３０|30日|1ヶ月).{0,10}(以内|間|可能)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "解約後のデータエクスポート期間を適切に確保",
        "legal_basis": "GDPR20条（データポータビリティ）参照"
    },
    
    "reasonable_tos_change": {
        "pattern": r"(規約|約款).{0,10}(変更|改定).{0,20}(30|３０|30日|1ヶ月).{0,10}(前|以前).{0,10}(通知|告知).{0,20}(同意.{0,5}ない|解約.{0,5}可能)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "規約変更の30日前通知と解約権を保障",
        "legal_basis": "民法548条の4"
    },
    
    "proper_liability_cap": {
        "pattern": r"(故意|重過失).{0,10}(除き?|を除く|の場合を除き).{0,20}(賠償|責任).{0,10}(上限|限度).{0,20}(12|１２|12ヶ月|1年|過去.{0,5}年).{0,10}(利用料|料金)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "故意・重過失を除外した上での合理的な賠償上限",
        "legal_basis": "消費者契約法8条、業界標準"
    },
    
    "electronic_consumer_contract": {
        "pattern": r"(電子消費者契約法|電子契約法).{0,10}(に基づき|に従い|を遵守).{0,20}(確認画面|操作ミス|誤操作)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "電子消費者契約法の確認措置を遵守",
        "legal_basis": "電子消費者契約法3条"
    },
}


# =============================================================================
# M&A・投資契約 ホワイトリスト
# =============================================================================

MA_WHITELIST = {
    # 表明保証の標準パターン
    "standard_rw_knowledge_qualifier": {
        "pattern": r"(売主|対象会社).{0,10}(知る限り|知り得る限り|認識する限り).{0,20}(表明|保証)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "Knowledge Qualifier付きの表明保証。売主の認識範囲を限定する標準的手法",
        "legal_basis": "M&A実務慣行"
    },
    
    "standard_indemnity_cap": {
        "pattern": r"(補償|賠償).{0,10}(上限|Cap|キャップ).{0,20}(買収価格|取引価額).{0,10}の.{0,5}(\d+).{0,5}(%|パーセント)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "買収価格の一定割合を上限とする標準的な補償Cap",
        "legal_basis": "M&A実務慣行"
    },
    
    "standard_indemnity_basket": {
        "pattern": r"(補償|賠償).{0,20}(basket|バスケット|最低額|閾値).{0,20}(超える|超過した).{0,10}(場合|部分)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "少額請求を除外するBasket条項。標準的な実務慣行",
        "legal_basis": "M&A実務慣行"
    },
    
    "mac_clause_standard": {
        "pattern": r"(MAC|Material Adverse Change|重大な悪影響).{0,30}(定義|意味).{0,20}(一般的な経済状況|市場全体|業界全体).{0,10}(除く|除外)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "標準的なMAC条項の除外規定（市場全体の変動等を除外）",
        "legal_basis": "M&A実務慣行"
    },
}


# =============================================================================
# 金融商品取引 ホワイトリスト
# =============================================================================

FINANCE_WHITELIST = {
    "suitability_principle": {
        "pattern": r"(適合性|適合性の原則).{0,20}(金融商品取引法|金商法).{0,10}(40条|四十条).{0,10}(に基づき|に従い)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "適合性原則に基づく説明義務の履行",
        "legal_basis": "金融商品取引法40条"
    },
    
    "risk_explanation_proper": {
        "pattern": r"(元本|元金).{0,10}(損失|毀損).{0,10}(可能性|リスク|おそれ).{0,20}(説明|理解|確認)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "元本損失リスクの適切な説明",
        "legal_basis": "金融商品取引法37条の3"
    },
    
    "cooling_off_provision": {
        "pattern": r"(クーリング・オフ|クーリングオフ).{0,20}(8日|八日|8日間).{0,10}(以内|間).{0,10}(解除|撤回|取消)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "法定のクーリング・オフ期間を確保",
        "legal_basis": "特定商取引法、金融商品販売法"
    },
}


# =============================================================================
# 消費者契約 一般 ホワイトリスト
# =============================================================================

CONSUMER_GENERAL_WHITELIST = {
    "consumer_contract_act_compliant": {
        "pattern": r"(消費者契約法|消契法).{0,10}(に基づき|に従い|を遵守).{0,20}(契約|取引|条項)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "消費者契約法の遵守を明示",
        "legal_basis": "消費者契約法"
    },
    
    "proper_cancellation_notice": {
        "pattern": r"(解約|解除|退会).{0,20}(14|15|7|１４|１５|７).{0,5}(日|日間).{0,10}(前|以前).{0,10}(通知|届出|申出)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "合理的な解約予告期間（7〜15日）",
        "legal_basis": "消費者契約法、特定商取引法"
    },
    
    "tokushoho_compliant": {
        "pattern": r"(特定商取引法|特商法).{0,10}(に基づき|に従い|を遵守).{0,20}(表示|記載|広告)",
        "verdict": WhitelistVerdict.OK_COMPLIANT,
        "reason": "特定商取引法の表示義務を遵守",
        "legal_basis": "特定商取引法11条等"
    },
    
    "adr_available": {
        "pattern": r"(ADR|裁判外紛争解決|調停|あっせん).{0,20}(利用|申立て|手続き).{0,10}(できる|可能|妨げない)",
        "verdict": WhitelistVerdict.OK_STANDARD,
        "reason": "ADRへのアクセスを保障",
        "legal_basis": "裁判外紛争解決手続の利用の促進に関する法律"
    },
}


# =============================================================================
# メインエンジン
# =============================================================================

class IndustryWhitelist:
    """業界別ホワイトリスト検出エンジン"""
    
    VERSION = "1.59.0"
    
    def __init__(self):
        self.domain_patterns = {
            "LABOR": LABOR_WHITELIST,
            "REALESTATE": REALESTATE_WHITELIST,
            "IT_SAAS": ITSAAS_WHITELIST,
            "MA": MA_WHITELIST,
            "FINANCE": FINANCE_WHITELIST,
            "CONSUMER_GENERAL": CONSUMER_GENERAL_WHITELIST,
        }
    
    def detect(self, clause_text: str, domain: Optional[str] = None) -> List[WhitelistResult]:
        """ホワイトリストパターンを検出"""
        results = []
        
        # 特定ドメインのみ、または全ドメインをチェック
        domains_to_check = [domain] if domain else self.domain_patterns.keys()
        
        for check_domain in domains_to_check:
            if check_domain not in self.domain_patterns:
                continue
                
            patterns = self.domain_patterns[check_domain]
            for pattern_name, pattern_info in patterns.items():
                match = re.search(pattern_info["pattern"], clause_text)
                if match:
                    results.append(WhitelistResult(
                        verdict=pattern_info["verdict"],
                        pattern_name=pattern_name,
                        matched_text=match.group(0),
                        reason=pattern_info["reason"],
                        applicable_domain=check_domain,
                        legal_basis=pattern_info["legal_basis"]
                    ))
        
        return results
    
    def is_whitelisted(self, clause_text: str, domain: Optional[str] = None) -> bool:
        """条項がホワイトリストに該当するか"""
        results = self.detect(clause_text, domain)
        return len(results) > 0
    
    def get_statistics(self) -> Dict:
        """統計情報"""
        total = sum(len(patterns) for patterns in self.domain_patterns.values())
        by_domain = {name: len(patterns) for name, patterns in self.domain_patterns.items()}
        
        return {
            "version": self.VERSION,
            "total_whitelist_patterns": total,
            "by_domain": by_domain,
            "domains": list(self.domain_patterns.keys())
        }


# エクスポート
industry_whitelist = IndustryWhitelist()
