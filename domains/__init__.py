"""
VERITAS Domain Packs
Version: 1.58.0

利用可能なドメインパック:
- M&A Pack: M&A・投資契約向け
- Finance Pack: 金融商品取引向け
- Labor Pack: 労働契約向け (v158追加)
- RealEstate Pack: 不動産契約向け (v158追加)
- IT/SaaS Pack: IT・SaaSサービス契約向け (v158追加)
"""

from .labor_pack import LaborPack, labor_pack, LaborVerdict, LaborCheckResult
from .realestate_pack import RealEstatePack, realestate_pack, RealEstateVerdict, RealEstateCheckResult
from .it_saas_pack import ITSaaSPack, it_saas_pack, ITSaaSVerdict, ITSaaSCheckResult

# v156からの既存Pack（互換性維持）
try:
    from .ma_pack import MAPack, ma_pack
    from .fin_pack import FinancePack, fin_pack
except ImportError:
    # 既存Packがない場合はスキップ
    pass


__all__ = [
    # Labor Pack
    "LaborPack",
    "labor_pack", 
    "LaborVerdict",
    "LaborCheckResult",
    
    # RealEstate Pack
    "RealEstatePack",
    "realestate_pack",
    "RealEstateVerdict", 
    "RealEstateCheckResult",
    
    # IT/SaaS Pack
    "ITSaaSPack",
    "it_saas_pack",
    "ITSaaSVerdict",
    "ITSaaSCheckResult",
]

# パック一覧
AVAILABLE_PACKS = {
    "LABOR": labor_pack,
    "REALESTATE": realestate_pack,
    "IT_SAAS": it_saas_pack,
}

def get_pack(domain: str):
    """ドメイン名からPackを取得"""
    return AVAILABLE_PACKS.get(domain.upper())

def list_packs():
    """利用可能なPackの一覧"""
    return {
        name: pack.get_statistics() 
        for name, pack in AVAILABLE_PACKS.items()
    }
