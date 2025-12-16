"""
VERITAS Domain Pack: Labor (労働契約)
Version: 1.58.0

対象: 雇用契約、出向契約、派遣契約、業務委託（偽装請負リスク）
主要法令: 労働基準法、職業安定法、労働者派遣法、労働契約法

設計原則:
- FALSE_OK=0 の死守
- Core不変、知識分離
- 労働者保護の観点からの厳格判定
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class LaborVerdict(Enum):
    """労働契約特有の判定結果"""
    NG_CRITICAL = "NG_CRITICAL"      # 労基法違反等、刑事罰リスク
    NG = "NG"                         # 法令違反、無効条項
    REVIEW_HIGH = "REVIEW_HIGH"       # 高リスク要確認
    REVIEW_MED = "REVIEW_MED"         # 中リスク要確認
    OK_CAUTION = "OK_CAUTION"         # 条件付きOK
    OK = "OK"                         # 問題なし


@dataclass
class LaborCheckResult:
    """労働契約チェック結果"""
    verdict: LaborVerdict
    trigger_name: str
    matched_text: str
    check_points: List[str]
    legal_basis: str
    rewrite_suggestion: Optional[str] = None


# =============================================================================
# NG_CRITICAL: 刑事罰リスクのある重大違反
# =============================================================================

LABOR_NG_CRITICAL_TRIGGERS = {
    # 偽装請負（職安法44条、労働者派遣法違反）
    "disguised_employment_command": {
        "pattern": r"(発注者|委託者|甲).{0,20}(指揮|命令|指示).{0,10}(従う|受ける|服する|遂行)",
        "check_points": [
            "業務委託なのに指揮命令権を規定している",
            "実態が労働者派遣に該当する可能性",
            "職安法44条（労働者供給事業の禁止）違反リスク"
        ],
        "legal_basis": "職業安定法44条、労働者派遣法",
        "rewrite": "「乙は、甲の業務要件に基づき、乙の責任において業務を遂行する」"
    },
    
    "disguised_employment_workplace": {
        "pattern": r"(発注者|委託者|甲).{0,10}(事業所|オフィス|職場).{0,10}(常駐|勤務|出勤)",
        "check_points": [
            "業務委託なのに常駐義務を規定",
            "勤務場所の指定は雇用関係の徴表",
            "偽装請負の典型パターン"
        ],
        "legal_basis": "職業安定法44条、労働者派遣法",
        "rewrite": "「業務遂行場所は乙が合理的に決定する。ただし、業務の性質上必要な場合は甲乙協議の上定める」"
    },
    
    "disguised_employment_time": {
        "pattern": r"(発注者|委託者|甲).{0,10}(勤務時間|就業時間|始業|終業).{0,10}(定める|指定|従う)",
        "check_points": [
            "業務委託なのに勤務時間を指定",
            "時間管理は雇用関係の核心的要素",
            "偽装請負認定の強い根拠となる"
        ],
        "legal_basis": "職業安定法44条、労働基準法",
        "rewrite": "「業務遂行の時間配分は乙が自己の裁量により決定する」"
    },
    
    # 強制労働（労基法5条）
    "forced_labor": {
        "pattern": r"(退職|離職|辞職).{0,20}(禁止|できない|認めない|許可.{0,5}要)",
        "check_points": [
            "退職の自由を制限する条項",
            "労働基準法5条（強制労働の禁止）違反",
            "憲法22条（職業選択の自由）にも抵触"
        ],
        "legal_basis": "労働基準法5条、憲法22条",
        "rewrite": "「従業員は、民法627条に基づき退職することができる」"
    },
    
    # 賠償予定（労基法16条）
    "penalty_clause": {
        "pattern": r"(違約金|損害賠償.{0,5}予定|ペナルティ).{0,20}(○|〇|\d+).{0,5}(万円|円)",
        "check_points": [
            "損害賠償額の予定を定めている",
            "労働基準法16条違反（賠償予定の禁止）",
            "実損害の証明なく定額請求は違法"
        ],
        "legal_basis": "労働基準法16条",
        "rewrite": "「損害賠償については、実際に生じた損害の範囲で協議の上定める」"
    },
    
    # 前借金相殺（労基法17条）
    "advance_deduction": {
        "pattern": r"(前借|貸付|立替).{0,20}(賃金|給与|報酬).{0,10}(相殺|控除|差引)",
        "check_points": [
            "前借金と賃金の相殺を規定",
            "労働基準法17条違反",
            "労働の強制につながる"
        ],
        "legal_basis": "労働基準法17条",
        "rewrite": "削除すべき条項"
    },
    
    # 解雇予告なし即時解雇（労基法20条違反）
    "immediate_dismissal": {
        "pattern": r"(即時|即日|直ちに).{0,10}(解雇|解約|契約終了).{0,20}(できる|する|行う)",
        "check_points": [
            "即時解雇を無条件で認める条項",
            "労働基準法20条の解雇予告義務違反",
            "30日前予告または予告手当が必要"
        ],
        "legal_basis": "労働基準法20条",
        "rewrite": "「解雇する場合は、30日前に予告するか、30日分以上の平均賃金を支払う」"
    },
}


# =============================================================================
# NG: 法令違反・無効条項
# =============================================================================

LABOR_NG_TRIGGERS = {
    # 競業避止義務過剰
    "excessive_noncompete_period": {
        "pattern": r"(競業|競合|同業).{0,20}(禁止|避止|してはならない).{0,30}(\d+)\s*(年|ヶ年|箇年)",
        "check_points": [
            "競業避止期間が長すぎる可能性",
            "2年超は無効となる可能性が高い",
            "職業選択の自由との均衡を確認"
        ],
        "legal_basis": "憲法22条、判例法理",
        "validate": lambda m: int(m.group(3)) > 2,
        "rewrite": "「退職後1年間は、会社と競合する事業に従事しない」"
    },
    
    "excessive_noncompete_scope": {
        "pattern": r"(全国|日本国内|国内外|全世界|すべての地域).{0,20}(競業|競合|同業|就職).{0,10}(禁止|してはならない|できない)|(競業|競合|同業).{0,20}(全国|日本国内|国内外|全世界|すべての地域)",
        "check_points": [
            "競業避止の地理的範囲が過度に広い",
            "合理的な範囲に限定すべき",
            "無効となる可能性が高い"
        ],
        "legal_basis": "判例法理（競業避止義務の有効要件）",
        "rewrite": "「会社の事業所が所在する都道府県内において」"
    },
    
    # 賃金全額払い違反（労基法24条）
    "wage_deduction_illegal": {
        "pattern": r"(賃金|給与|報酬).{0,20}(控除|差引|天引き).{0,20}(できる|する|行う)",
        "check_points": [
            "賃金からの一方的控除を認める条項",
            "労働基準法24条（全額払いの原則）違反",
            "労使協定なき控除は違法"
        ],
        "legal_basis": "労働基準法24条",
        "rewrite": "「賃金からの控除は、法令に定めるもの及び労使協定に基づくものに限る」"
    },
    
    # 有給休暇買上げ強制
    "forced_leave_buyout": {
        "pattern": r"(有給|年休|年次休暇).{0,20}(買上げ|買い上げ|金銭.{0,5}換算)",
        "check_points": [
            "有給休暇の買上げを強制する条項",
            "労働者の休暇取得権を侵害",
            "退職時の未消化分買上げは適法"
        ],
        "legal_basis": "労働基準法39条",
        "rewrite": "「年次有給休暇は、労働者の請求に基づき取得する」"
    },
    
    # 出向の実質派遣
    "secondment_as_dispatch": {
        "pattern": r"出向.{0,30}(出向先|受入先).{0,10}(指揮|命令|管理).{0,10}(下|従う)",
        "check_points": [
            "出向だが実態は労働者派遣の可能性",
            "出向元との雇用関係の実質を確認",
            "派遣法の適用漏れリスク"
        ],
        "legal_basis": "労働者派遣法、労働契約法14条",
        "rewrite": "「出向期間中も、乙と従業員との雇用関係は継続する」"
    },
}


# =============================================================================
# REVIEW_HIGH: 高リスク要確認
# =============================================================================

LABOR_REVIEW_HIGH_TRIGGERS = {
    # 試用期間
    "long_probation": {
        "pattern": r"(試用|試傭|見習).{0,10}期間.{0,20}(\d+)\s*(ヶ月|箇月|か月|月間)",
        "check_points": [
            "試用期間の長さを確認",
            "6ヶ月超は合理性が問われる",
            "延長規定の有無を確認"
        ],
        "legal_basis": "判例法理",
        "validate": lambda m: int(m.group(2)) > 6
    },
    
    # 固定残業代
    "fixed_overtime": {
        "pattern": r"(固定残業|みなし残業|定額残業).{0,20}(\d+)\s*(時間|h)",
        "check_points": [
            "固定残業代の時間数を確認",
            "45時間超は36協定の限度超過",
            "超過分の別途支給規定を確認"
        ],
        "legal_basis": "労働基準法36条、37条"
    },
    
    # 転勤条項
    "broad_transfer": {
        "pattern": r"(転勤|異動|配置転換).{0,20}(全国|どこでも|いずれ.{0,5}事業所|命じ.{0,5}できる)",
        "check_points": [
            "広範な転勤命令権の規定",
            "労働者への不利益の程度を確認",
            "育児・介護責任との調整を確認"
        ],
        "legal_basis": "労働契約法3条、育児介護休業法26条"
    },
    
    # 秘密保持と競業避止の包括条項
    "broad_confidentiality": {
        "pattern": r"(業務上.{0,5}知り得た|在職中.{0,5}知った).{0,10}(一切|すべて|全て).{0,10}(秘密|機密)",
        "check_points": [
            "秘密保持の範囲が過度に広い可能性",
            "退職後の就業制限につながるリスク",
            "具体的な秘密情報の定義を確認"
        ],
        "legal_basis": "不正競争防止法、判例法理"
    },
    
    # 出向期間
    "long_secondment": {
        "pattern": r"出向.{0,20}期間.{0,20}(\d+)\s*(年|ヶ年)",
        "check_points": [
            "出向期間の妥当性を確認",
            "3年超は「転籍」との区別が曖昧に",
            "復帰条件を明確化すべき"
        ],
        "legal_basis": "労働契約法14条",
        "validate": lambda m: int(m.group(1)) > 3
    },
    
    # 副業禁止
    "side_job_prohibition": {
        "pattern": r"(副業|兼業|二重就職).{0,10}(禁止|してはならない|認めない)",
        "check_points": [
            "副業禁止の合理性を確認",
            "競業・情報漏洩リスクがない限り原則自由",
            "厚労省モデル就業規則は副業容認"
        ],
        "legal_basis": "厚生労働省モデル就業規則、判例法理"
    },
}


# =============================================================================
# REVIEW_MED: 中リスク要確認
# =============================================================================

LABOR_REVIEW_MED_TRIGGERS = {
    # 服務規律
    "broad_discipline": {
        "pattern": r"(服務規律|就業規則).{0,20}(遵守|従う|服する).{0,10}(義務|もの)",
        "check_points": [
            "就業規則の周知を確認",
            "不合理な規律がないか確認",
            "変更手続きの妥当性を確認"
        ],
        "legal_basis": "労働基準法89条、労働契約法7条"
    },
    
    # 懲戒事由
    "disciplinary_grounds": {
        "pattern": r"(懲戒|制裁).{0,20}(解雇|処分|減給).{0,20}(できる|する)",
        "check_points": [
            "懲戒事由の明確性を確認",
            "処分の相当性を確認",
            "手続保障（弁明の機会）を確認"
        ],
        "legal_basis": "労働基準法89条9号、労働契約法15条"
    },
    
    # 研修費用返還
    "training_cost_return": {
        "pattern": r"(研修|教育|訓練).{0,10}(費用|経費).{0,20}(返還|返済|償還)",
        "check_points": [
            "研修費用返還条項の有効性を確認",
            "労基法16条（賠償予定禁止）との関係",
            "実費相当かつ合理的期間内か確認"
        ],
        "legal_basis": "労働基準法16条、判例法理"
    },
}


# =============================================================================
# OK_CAUTION: 条件付きOK（労働者保護規定あり）
# =============================================================================

LABOR_OK_CAUTION_PATTERNS = {
    "proper_dismissal_notice": {
        "pattern": r"(解雇|雇止め).{0,20}(30日|１ヶ月|1ヶ月).{0,10}(前|以前).{0,10}(予告|通知)",
        "check_points": [
            "解雇予告期間が法定基準を満たしている",
            "予告手当の代替規定も確認"
        ],
        "legal_basis": "労働基準法20条"
    },
    
    "proper_overtime_pay": {
        "pattern": r"(時間外|残業|休日).{0,10}(労働|勤務).{0,20}(25|50|35|60)\s*(%|パーセント|割増)",
        "check_points": [
            "割増賃金率が法定基準以上",
            "計算基礎の確認を推奨"
        ],
        "legal_basis": "労働基準法37条"
    },
    
    "proper_leave": {
        "pattern": r"(年次有給休暇|年休).{0,20}(10|１０).{0,5}(日|日間).{0,10}(付与|与える)",
        "check_points": [
            "法定の年次有給休暇を規定",
            "継続勤務に応じた加算を確認"
        ],
        "legal_basis": "労働基準法39条"
    },
}


# =============================================================================
# メインエンジン
# =============================================================================

class LaborPack:
    """労働契約ドメインパック"""
    
    VERSION = "1.58.0"
    DOMAIN = "LABOR"
    
    def __init__(self):
        self.ng_critical = LABOR_NG_CRITICAL_TRIGGERS
        self.ng = LABOR_NG_TRIGGERS
        self.review_high = LABOR_REVIEW_HIGH_TRIGGERS
        self.review_med = LABOR_REVIEW_MED_TRIGGERS
        self.ok_caution = LABOR_OK_CAUTION_PATTERNS
    
    def analyze(self, clause_text: str) -> List[LaborCheckResult]:
        """条項を分析し、労働法リスクを検出"""
        results = []
        
        # NG_CRITICAL チェック
        for name, trigger in self.ng_critical.items():
            match = re.search(trigger["pattern"], clause_text)
            if match:
                results.append(LaborCheckResult(
                    verdict=LaborVerdict.NG_CRITICAL,
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
                # validate関数がある場合は追加チェック
                if "validate" in trigger:
                    if not trigger["validate"](match):
                        continue
                results.append(LaborCheckResult(
                    verdict=LaborVerdict.NG,
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
                if "validate" in trigger:
                    if not trigger["validate"](match):
                        continue
                results.append(LaborCheckResult(
                    verdict=LaborVerdict.REVIEW_HIGH,
                    trigger_name=name,
                    matched_text=match.group(0),
                    check_points=trigger["check_points"],
                    legal_basis=trigger["legal_basis"]
                ))
        
        # REVIEW_MED チェック
        for name, trigger in self.review_med.items():
            match = re.search(trigger["pattern"], clause_text)
            if match:
                results.append(LaborCheckResult(
                    verdict=LaborVerdict.REVIEW_MED,
                    trigger_name=name,
                    matched_text=match.group(0),
                    check_points=trigger["check_points"],
                    legal_basis=trigger["legal_basis"]
                ))
        
        # OK_CAUTION チェック（他にNGがない場合のみ）
        if not any(r.verdict in [LaborVerdict.NG_CRITICAL, LaborVerdict.NG] for r in results):
            for name, pattern_info in self.ok_caution.items():
                match = re.search(pattern_info["pattern"], clause_text)
                if match:
                    results.append(LaborCheckResult(
                        verdict=LaborVerdict.OK_CAUTION,
                        trigger_name=name,
                        matched_text=match.group(0),
                        check_points=pattern_info["check_points"],
                        legal_basis=pattern_info["legal_basis"]
                    ))
        
        return results
    
    def get_worst_verdict(self, results: List[LaborCheckResult]) -> LaborVerdict:
        """最も厳しい判定を返す"""
        if not results:
            return LaborVerdict.OK
        
        priority = [
            LaborVerdict.NG_CRITICAL,
            LaborVerdict.NG,
            LaborVerdict.REVIEW_HIGH,
            LaborVerdict.REVIEW_MED,
            LaborVerdict.OK_CAUTION,
            LaborVerdict.OK
        ]
        
        for verdict in priority:
            if any(r.verdict == verdict for r in results):
                return verdict
        
        return LaborVerdict.OK
    
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
labor_pack = LaborPack()
