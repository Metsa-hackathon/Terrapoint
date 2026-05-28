from pydantic import BaseModel
from typing import Optional


class KatasterInfo(BaseModel):
    number: str
    pindala_ha: float
    mets_pindala_ha: Optional[float] = None
    sihtotstarve: Optional[str] = None
    omvorm: Optional[str] = None
    maks_hind: Optional[int] = None
    mk_nimi: Optional[str] = None
    ov_nimi: Optional[str] = None
    l_aadress: Optional[str] = None
    geometry: Optional[dict] = None


class SpeciesComposition(BaseModel):
    puuliik: str
    puuliik_kood: str
    osakaal: int
    vanus: Optional[int] = None
    korgus: Optional[float] = None
    tagavara: Optional[float] = None


class MetsaData(BaseModel):
    puuliik: str
    puuliik_kood: str
    vanus: int
    tagavara_y_ha: float
    boniteet: str
    boniteedi_kood: int
    raievanus: Optional[float] = None
    korgus: Optional[float] = None
    pindala_ha: float
    taius_1: Optional[float] = None
    kuivendatud: bool = False
    tuleohu_kood: Optional[str] = None
    liikide_koosseis: list[SpeciesComposition] = []


class Vaartus(BaseModel):
    tagavara_m3: float
    price_per_m3: float
    log_price: float
    pulp_price: float
    total_value_eur: float
    value_per_ha: float


class Sinik(BaseModel):
    biomass_tons_ha: float
    total_biomass_tons_ha: float
    carbon_tons_ha: float
    co2_tons_ha: float
    co2_tons_total: float
    potential_income_eur: float


class Kitsendus(BaseModel):
    tyyp: str
    kirjeldus: str
    allikas: str


class Toetus(BaseModel):
    nimi: str
    summa: str
    asutus: str
    sobib: bool
    taotlusvoor: Optional[str] = None


class Riskid(BaseModel):
    raievanus: Optional[dict] = None
    yrask: Optional[dict] = None
    terviseindeks: Optional[int] = None
    karuputk: bool = False
    lageraieala: Optional[str] = None


class SearchResponse(BaseModel):
    kataster: KatasterInfo
    mets: Optional[MetsaData] = None
    vaartus: Optional[Vaartus] = None
    sinik: Optional[Sinik] = None
    kitsendused: list[Kitsendus] = []
    toetused: list[Toetus] = []
    riskid: Riskid = Riskid()
    meta: dict = {}
