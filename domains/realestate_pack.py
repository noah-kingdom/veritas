"""
VERITAS Domain Pack: Real Estate (不動産契約)
Version: 1.58.0

対象: 賃貸借契約、不動産売買契約、設備貸与契約、使用貸借契約
主要法令: 借地借家法、宅地建物取引業法、民法（賃貸借）

設計原則:
- FALSE_OK=0 の死守
- Core不変、知識分離
- 借主・買主保護の観点からの厳格判定
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class RealEstateVerdict(Enum):
    """不動産契約特有の判定結果"""
    NG_CRITICAL = "NG_CRITICAL"      # 強行規定違反（無効）
    NG = "NG"                         # 法令違反、不当条項
    REVIEW_HIGH = "REVIEW_HIGH"       # 高リスク要確認
    REVIEW_MED = "REVIEW_MED"         # 中リスク要確認
    OK_CAUTION = "OK_CAUTION"         # 条件付きOK
    OK = "OK"                         # 問題なし


@dataclass
class RealEstateCheckResult:
    """不動産契約チェック結果"""
    verdict: RealEstateVerdict
    trigger_name: str
    matched_text: str
    check_points: List[str]
    legal_basis: str
    rewrite_suggestion: Optional[str] = None


# =============================================================================
# NG_CRITICAL: 強行規定違反（借地借家法の強行規定等）
# =============================================================================

REALESTATE_NG_CRITICAL_TRIGGERS = {
    # 借地借家法の強行規定違反
    "deny_renewal_right": {
        "pattern": r"(更新|契約継続).{0,20}(請求|権利).{0,10}(放棄|できない|認めない|有しない)",
        "check_points": [
            "借地借家法上の更新請求権を否定する条項",
            "借地借家法26条・28条は強行規定",
            "借主に不利な特約は無効"
        ],
        "legal_basis": "借地借家法26条、28条、30条",
        "rewrite": "削除すべき条項（法定更新権は放棄できない）"
    },
    
    "deny_buyback_right": {
        "pattern": r"(造作|設備).{0,10}(買取|買い取り).{0,10}(請求|権利).{0,10}(放棄|できない|認めない)",
        "check_points": [
            "造作買取請求権を否定する条項",
            "借地借家法33条は任意規定だが確認要",
            "特約で排除可能だが借主への説明が必要"
        ],
        "legal_basis": "借地借家法33条",
        "rewrite": "「造作買取請求権については、別途協議の上定める」"
    },
    
    # 敷金返還拒否
    "deny_deposit_return": {
        "pattern": r"(敷金|保証金).{0,20}(返還|返却).{0,10}(しない|できない|放棄|一切)",
        "check_points": [
            "敷金返還義務を全面的に否定する条項",
            "民法622条の2に違反",
            "消費者契約法10条でも無効となり得る"
        ],
        "legal_basis": "民法622条の2、消費者契約法10条",
        "rewrite": "「敷金は、賃料等の未払いを控除した残額を返還する」"
    },
    
    # 賃借権譲渡・転貸の全面禁止（事業用は別）
    "absolute_sublease_ban_residential": {
        "pattern": r"(住居|居住用).{0,30}(譲渡|転貸).{0,10}(一切|絶対|いかなる).{0,10}(禁止|できない)",
        "check_points": [
            "居住用賃貸の転貸禁止は通常有効だが確認要",
            "背信性がない転貸は解除できない場合あり",
            "承諾に代わる許可制度（借地借家法19条）"
        ],
        "legal_basis": "民法612条、借地借家法19条"
    },
    
    # 宅建業法違反（重要事項説明義務免除）
    "waive_important_matters": {
        "pattern": r"(重要事項|35条|宅建業法).{0,20}(説明|書面).{0,10}(不要|省略|免除|放棄)",
        "check_points": [
            "重要事項説明義務は免除できない",
            "宅建業法35条違反",
            "業法違反は刑事罰あり"
        ],
        "legal_basis": "宅地建物取引業法35条",
        "rewrite": "削除すべき条項"
    },
}


# =============================================================================
# NG: 不当条項・法令違反
# =============================================================================

REALESTATE_NG_TRIGGERS = {
    # 原状回復の過剰負担
    "excessive_restoration": {
        "pattern": r"(原状回復|原状に復する).{0,30}(通常|経年|自然).{0,10}(損耗|劣化|摩耗).{0,10}(含む|負担)",
        "check_points": [
            "通常損耗まで借主負担としている",
            "国交省ガイドラインに反する",
            "消費者契約法10条で無効となり得る"
        ],
        "legal_basis": "民法621条、国交省原状回復ガイドライン",
        "rewrite": "「通常の使用による損耗及び経年変化を除き、原状に復する」"
    },
    
    # 違約金過剰
    "excessive_penalty": {
        "pattern": r"違約金.{0,20}?賃料.{0,5}?(\d+).{0,5}?(ヶ月|箇月|か月|ヵ月)|賃料.{0,5}?(\d+).{0,5}?(ヶ月|箇月|か月|ヵ月).{0,10}?(違約金|支払)",
        "check_points": [
            "違約金が賃料の何ヶ月分かを確認",
            "6ヶ月超は過大と判断される可能性",
            "消費者契約法9条で無効となり得る"
        ],
        "legal_basis": "消費者契約法9条1号",
        "validate": lambda m: int(m.group(1) or m.group(3) or "0") > 6,
        "rewrite": "「中途解約の場合、賃料1ヶ月分相当額を違約金として支払う」"
    },
    
    # 一方的賃料増額
    "unilateral_rent_increase": {
        "pattern": r"(賃料|家賃).{0,20}(貸主|甲|オーナー).{0,10}(判断|決定|意向).{0,10}(増額|変更|改定|できる)|(賃料|家賃).{0,10}(増額|値上げ|改定|変更).{0,20}(一方的|通知のみ|貸主.{0,5}判断|甲.{0,5}判断)",
        "check_points": [
            "借地借家法32条の協議・調停・裁判を経ない増額",
            "一方的な増額は無効",
            "借主の同意なき増額は認められない"
        ],
        "legal_basis": "借地借家法32条",
        "rewrite": "「賃料の増減は、借地借家法32条に基づき協議の上定める」"
    },
    
    # 即時解除条項（居住用）
    "immediate_termination_residential": {
        "pattern": r"(居住|住居).{0,30}(賃料|家賃).{0,10}(滞納|延滞|遅延).{0,20}(直ちに|即時|即日).{0,10}(解除|解約)",
        "check_points": [
            "1回の賃料滞納で即時解除は過酷",
            "信頼関係破壊法理により無効となり得る",
            "通常3ヶ月程度の滞納が必要"
        ],
        "legal_basis": "判例法理（信頼関係破壊の法理）",
        "rewrite": "「賃料を3ヶ月以上滞納し、催告後相当期間内に支払わない場合、解除できる」"
    },
    
    # 更新料過剰
    "excessive_renewal_fee": {
        "pattern": r"(更新料|更新費用).{0,20}(賃料|家賃).{0,10}(\d+\.?\d*)\s*(ヶ月|箇月|倍)",
        "check_points": [
            "更新料が賃料の何ヶ月分かを確認",
            "2ヶ月超は高額と判断される可能性",
            "最高裁判例で一定の有効性は認められるが限度あり"
        ],
        "legal_basis": "最判平成23年7月15日",
        "validate": lambda m: float(m.group(3)) > 2
    },
    
    # 瑕疵担保免責（売買）
    "waive_warranty_sale": {
        "pattern": r"(売買|売却).{0,30}(瑕疵|欠陥|不適合).{0,20}(一切|すべて|いかなる).{0,10}(免責|責任.{0,5}負わない)",
        "check_points": [
            "契約不適合責任の全面免責",
            "消費者への売却では消費者契約法8条で無効",
            "事業者間でも信義則上問題となり得る"
        ],
        "legal_basis": "民法562条〜、消費者契約法8条",
        "rewrite": "「売主は、引渡後○年間、契約不適合責任を負う」"
    },
}


# =============================================================================
# REVIEW_HIGH: 高リスク要確認
# =============================================================================

REALESTATE_REVIEW_HIGH_TRIGGERS = {
    # 定期借家
    "fixed_term_lease": {
        "pattern": r"(定期借家|定期建物賃貸借|更新.{0,5}ない).{0,20}(契約|賃貸借)",
        "check_points": [
            "定期借家契約は更新がない点を確認",
            "書面による説明義務（借地借家法38条2項）",
            "説明なき場合は普通借家となる"
        ],
        "legal_basis": "借地借家法38条"
    },
    
    # 賃料改定条項
    "rent_revision_clause": {
        "pattern": r"(賃料|家賃).{0,10}(改定|見直し).{0,20}(\d+)\s*(年|ヶ年)",
        "check_points": [
            "賃料改定の頻度と方法を確認",
            "借地借家法32条の協議義務との整合性",
            "自動増額条項は無効となり得る"
        ],
        "legal_basis": "借地借家法32条"
    },
    
    # 修繕義務の分担
    "repair_obligation": {
        "pattern": r"(修繕|修理|補修).{0,20}(借主|賃借人|乙).{0,10}(負担|費用|義務)",
        "check_points": [
            "借主負担の修繕範囲を確認",
            "通常は貸主が修繕義務を負う（民法606条）",
            "小修繕のみ借主負担は有効"
        ],
        "legal_basis": "民法606条"
    },
    
    # 連帯保証人
    "joint_guarantor": {
        "pattern": r"(連帯保証|連帯して保証).{0,20}(極度額|限度額)",
        "check_points": [
            "極度額の定めがあるか確認",
            "2020年民法改正で極度額必須",
            "極度額なき保証契約は無効"
        ],
        "legal_basis": "民法465条の2"
    },
    
    # 解約予告期間
    "termination_notice": {
        "pattern": r"(解約|解除|退去).{0,10}(予告|通知).{0,20}(\d+)\s*(ヶ月|箇月|か月|日).{0,10}前",
        "check_points": [
            "解約予告期間の長さを確認",
            "居住用で6ヶ月超は長すぎる可能性",
            "借地借家法27条との整合性"
        ],
        "legal_basis": "借地借家法27条"
    },
    
    # 設備の所有権
    "equipment_ownership": {
        "pattern": r"(設備|機器|装置).{0,20}(所有権|帰属).{0,10}(貸主|賃貸人|甲)",
        "check_points": [
            "借主が設置した設備の取扱いを確認",
            "造作買取請求権との関係",
            "退去時の処理を明確化すべき"
        ],
        "legal_basis": "借地借家法33条"
    },
}


# =============================================================================
# REVIEW_MED: 中リスク要確認
# =============================================================================

REALESTATE_REVIEW_MED_TRIGGERS = {
    # 用途制限
    "use_restriction": {
        "pattern": r"(用途|使用目的).{0,20}(限定|制限|のみ|に限る)",
        "check_points": [
            "用途制限の合理性を確認",
            "事業用途の変更可能性を検討",
            "違反時のペナルティを確認"
        ],
        "legal_basis": "契約自由の原則"
    },
    
    # ペット禁止
    "pet_prohibition": {
        "pattern": r"(ペット|動物|犬|猫).{0,10}(禁止|飼育.{0,5}できない|不可)",
        "check_points": [
            "ペット禁止条項の有効性は認められる",
            "違反時の解除条項を確認",
            "補助犬は例外となることを確認"
        ],
        "legal_basis": "契約自由の原則、身体障害者補助犬法"
    },
    
    # 管理費・共益費
    "management_fee": {
        "pattern": r"(管理費|共益費|維持費).{0,20}(改定|変更|増額).{0,10}(できる|する)",
        "check_points": [
            "管理費改定の手続きを確認",
            "一方的増額の可否",
            "根拠の開示義務を確認"
        ],
        "legal_basis": "契約自由の原則"
    },
    
    # 抵当権設定通知
    "mortgage_notice": {
        "pattern": r"(抵当権|担保権).{0,20}(設定|登記).{0,20}(通知|同意|承諾)",
        "check_points": [
            "抵当権設定が賃借権に与える影響を確認",
            "競売時の賃借権の取扱い",
            "民法395条（抵当建物使用者の引渡猶予）"
        ],
        "legal_basis": "民法395条"
    },
}


# =============================================================================
# OK_CAUTION: 条件付きOK（標準的な不動産条項）
# =============================================================================

REALESTATE_OK_CAUTION_PATTERNS = {
    "proper_deposit": {
        "pattern": r"(敷金|保証金).{0,20}(賃料|家賃).{0,10}([1-3])\s*(ヶ月|箇月|か月)",
        "check_points": [
            "敷金が賃料1〜3ヶ月分で標準的",
            "返還条件を確認"
        ],
        "legal_basis": "民法622条の2"
    },
    
    "proper_renewal": {
        "pattern": r"(更新|継続).{0,20}(協議|合意).{0,10}(の上|により)",
        "check_points": [
            "合意更新の規定として適切",
            "法定更新との関係を確認"
        ],
        "legal_basis": "借地借家法26条"
    },
    
    "proper_restoration": {
        "pattern": r"(原状回復|原状に復する).{0,30}(通常|経年|自然).{0,10}(損耗|劣化).{0,10}(除く|除き)",
        "check_points": [
            "通常損耗を除外しており適切",
            "ガイドラインに沿った規定"
        ],
        "legal_basis": "民法621条、国交省ガイドライン"
    },
}


# =============================================================================
# メインエンジン
# =============================================================================

class RealEstatePack:
    """不動産契約ドメインパック"""
    
    VERSION = "1.58.0"
    DOMAIN = "REALESTATE"
    
    def __init__(self):
        self.ng_critical = REALESTATE_NG_CRITICAL_TRIGGERS
        self.ng = REALESTATE_NG_TRIGGERS
        self.review_high = REALESTATE_REVIEW_HIGH_TRIGGERS
        self.review_med = REALESTATE_REVIEW_MED_TRIGGERS
        self.ok_caution = REALESTATE_OK_CAUTION_PATTERNS
    
    def analyze(self, clause_text: str) -> List[RealEstateCheckResult]:
        """条項を分析し、不動産法リスクを検出"""
        results = []
        
        # NG_CRITICAL チェック
        for name, trigger in self.ng_critical.items():
            match = re.search(trigger["pattern"], clause_text)
            if match:
                results.append(RealEstateCheckResult(
                    verdict=RealEstateVerdict.NG_CRITICAL,
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
                results.append(RealEstateCheckResult(
                    verdict=RealEstateVerdict.NG,
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
                results.append(RealEstateCheckResult(
                    verdict=RealEstateVerdict.REVIEW_HIGH,
                    trigger_name=name,
                    matched_text=match.group(0),
                    check_points=trigger["check_points"],
                    legal_basis=trigger["legal_basis"]
                ))
        
        # REVIEW_MED チェック
        for name, trigger in self.review_med.items():
            match = re.search(trigger["pattern"], clause_text)
            if match:
                results.append(RealEstateCheckResult(
                    verdict=RealEstateVerdict.REVIEW_MED,
                    trigger_name=name,
                    matched_text=match.group(0),
                    check_points=trigger["check_points"],
                    legal_basis=trigger["legal_basis"]
                ))
        
        # OK_CAUTION チェック
        if not any(r.verdict in [RealEstateVerdict.NG_CRITICAL, RealEstateVerdict.NG] for r in results):
            for name, pattern_info in self.ok_caution.items():
                match = re.search(pattern_info["pattern"], clause_text)
                if match:
                    results.append(RealEstateCheckResult(
                        verdict=RealEstateVerdict.OK_CAUTION,
                        trigger_name=name,
                        matched_text=match.group(0),
                        check_points=pattern_info["check_points"],
                        legal_basis=pattern_info["legal_basis"]
                    ))
        
        return results
    
    def get_worst_verdict(self, results: List[RealEstateCheckResult]) -> RealEstateVerdict:
        """最も厳しい判定を返す"""
        if not results:
            return RealEstateVerdict.OK
        
        priority = [
            RealEstateVerdict.NG_CRITICAL,
            RealEstateVerdict.NG,
            RealEstateVerdict.REVIEW_HIGH,
            RealEstateVerdict.REVIEW_MED,
            RealEstateVerdict.OK_CAUTION,
            RealEstateVerdict.OK
        ]
        
        for verdict in priority:
            if any(r.verdict == verdict for r in results):
                return verdict
        
        return RealEstateVerdict.OK
    
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
            "patent_map": ["CLAIM_1", "CLAIM_2", "CLAIM_3", "CLAIM_4"]
        }


# エクスポート
realestate_pack = RealEstatePack()
