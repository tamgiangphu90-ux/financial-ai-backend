from dataclasses import asdict, dataclass
import os
from typing import Literal

from utils.config import get_settings


SourceStatus = Literal["active", "unavailable", "placeholder", "requires_api_key"]

REGION_GROUPS = (
    "Vietnam",
    "Asia",
    "Europe",
    "Americas",
    "Middle East",
    "Africa",
    "Global",
)


@dataclass(frozen=True)
class FinancialSource:
    name: str
    country: str
    region: str
    language: str
    source_type: str
    reliability_score: float
    freshness_level: str
    access_method: str
    url: str | None
    requires_api_key: bool
    status: SourceStatus
    data_types: list[str]
    notes: str | None = None

    @property
    def category(self) -> str:
        return self.source_type

    @property
    def public_url(self) -> str | None:
        return self.url

    def to_dict(self) -> dict:
        payload = asdict(self)
        if self.notes is None:
            payload.pop("notes")
        return payload


def _source(
    name: str,
    country: str,
    region: str,
    language: str,
    source_type: str,
    reliability_score: float,
    freshness_level: str,
    access_method: str,
    url: str | None,
    requires_api_key: bool,
    status: SourceStatus,
    data_types: list[str],
    notes: str | None = None,
) -> FinancialSource:
    if not url and status == "placeholder" and notes is None:
        notes = "URL needs verification"
    return FinancialSource(
        name=name,
        country=country,
        region=region,
        language=language,
        source_type=source_type,
        reliability_score=reliability_score,
        freshness_level=freshness_level,
        access_method=access_method,
        url=url,
        requires_api_key=requires_api_key,
        status=status,
        data_types=data_types,
        notes=notes,
    )


def _credential_status(env_name: str) -> SourceStatus:
    return "active" if os.getenv(env_name) else "requires_api_key"


settings = get_settings()


SOURCES: list[FinancialSource] = [
    # Vietnam
    _source("FireAnt", "Vietnam", "Vietnam", "vi", "market_data", 0.92, "realtime", "authorized_api", "https://fireant.vn", True, "active" if settings.fireant_token else "requires_api_key", ["quote", "fundamentals", "trades"], "Active FireAnt adapter requires FIREANT_TOKEN for realtime REST and quote hub data."),
    _source("CafeF", "Vietnam", "Vietnam", "vi", "market_data", 0.80, "delayed", "public_web", "https://cafef.vn", False, "active", ["quote", "news"]),
    _source("Vietstock", "Vietnam", "Vietnam", "vi", "market_data", 0.78, "delayed", "public_web", "https://vietstock.vn", False, "active", ["quote", "news", "reports"], "Adapter can fetch public Vietstock pages; structured quote parsing is limited."),
    _source("HOSE", "Vietnam", "Vietnam", "vi", "exchange", 0.95, "official", "public_web", "https://www.hsx.vn", False, "placeholder", ["listing", "announcements", "index"]),
    _source("HNX", "Vietnam", "Vietnam", "vi", "exchange", 0.95, "official", "public_web", "https://www.hnx.vn", False, "placeholder", ["listing", "announcements", "index"]),
    _source("UPCoM", "Vietnam", "Vietnam", "vi", "exchange", 0.92, "official", "public_web", "https://www.hnx.vn/vi-vn/upcom.html", False, "placeholder", ["listing", "announcements", "index"]),
    _source("SSC Vietnam", "Vietnam", "Vietnam", "vi", "regulator", 0.96, "official", "public_web", "https://ssc.gov.vn", False, "placeholder", ["disclosure", "regulation"]),
    _source("State Bank of Vietnam", "Vietnam", "Vietnam", "vi", "macro", 0.96, "official", "public_web", "https://www.sbv.gov.vn", False, "placeholder", ["rates", "fx", "monetary_policy"]),
    _source("General Statistics Office of Vietnam", "Vietnam", "Vietnam", "vi", "macro", 0.95, "official", "public_web", "https://www.gso.gov.vn", False, "placeholder", ["gdp", "cpi", "employment"]),
    _source("Vietnam Securities Depository and Clearing Corporation", "Vietnam", "Vietnam", "vi", "market_infrastructure", 0.94, "official", "public_web", "https://vsd.vn", False, "placeholder", ["settlement", "depository", "announcements"]),
    _source("Vietcombank Exchange Rates", "Vietnam", "Vietnam", "vi", "fx", 0.86, "daily", "public_web", "https://www.vietcombank.com.vn", False, "placeholder", ["fx", "rates"]),
    # Asia
    _source("Japan Exchange Group", "Japan", "Asia", "ja,en", "exchange", 0.94, "official", "public_web", "https://www.jpx.co.jp", False, "placeholder", ["listing", "announcements", "index"]),
    _source("Tokyo Stock Exchange", "Japan", "Asia", "ja,en", "exchange", 0.94, "official", "public_web", "https://www.jpx.co.jp/english/equities", False, "placeholder", ["listing", "announcements", "index"]),
    _source("Hong Kong Exchanges and Clearing", "Hong Kong", "Asia", "zh,en", "exchange", 0.94, "official", "public_web", "https://www.hkex.com.hk", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Singapore Exchange", "Singapore", "Asia", "en", "exchange", 0.93, "official", "public_web", "https://www.sgx.com", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Shanghai Stock Exchange", "China", "Asia", "zh,en", "exchange", 0.93, "official", "public_web", "https://english.sse.com.cn", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Shenzhen Stock Exchange", "China", "Asia", "zh,en", "exchange", 0.93, "official", "public_web", "https://www.szse.cn/English", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("National Stock Exchange of India", "India", "Asia", "en,hi", "exchange", 0.93, "official", "public_web", "https://www.nseindia.com", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("BSE India", "India", "Asia", "en,hi", "exchange", 0.92, "official", "public_web", "https://www.bseindia.com", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Korea Exchange", "South Korea", "Asia", "ko,en", "exchange", 0.93, "official", "public_web", "https://global.krx.co.kr", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Taiwan Stock Exchange", "Taiwan", "Asia", "zh,en", "exchange", 0.92, "official", "public_web", "https://www.twse.com.tw/en", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Stock Exchange of Thailand", "Thailand", "Asia", "th,en", "exchange", 0.92, "official", "public_web", "https://www.set.or.th", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Indonesia Stock Exchange", "Indonesia", "Asia", "id,en", "exchange", 0.91, "official", "public_web", "https://www.idx.co.id", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Bursa Malaysia", "Malaysia", "Asia", "ms,en", "exchange", 0.91, "official", "public_web", "https://www.bursamalaysia.com", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Philippine Stock Exchange", "Philippines", "Asia", "en", "exchange", 0.90, "official", "public_web", "https://www.pse.com.ph", False, "placeholder", ["listing", "announcements", "market_data"]),
    # Europe
    _source("European Central Bank", "European Union", "Europe", "en", "central_bank", 0.96, "official", "public_api", "https://www.ecb.europa.eu", False, "placeholder", ["rates", "fx", "monetary_policy"]),
    _source("Eurostat", "European Union", "Europe", "en", "macro", 0.95, "official", "public_api", "https://ec.europa.eu/eurostat", False, "placeholder", ["macro", "statistics"]),
    _source("London Stock Exchange", "United Kingdom", "Europe", "en", "exchange", 0.94, "official", "public_web", "https://www.londonstockexchange.com", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Bank of England", "United Kingdom", "Europe", "en", "central_bank", 0.96, "official", "public_api", "https://www.bankofengland.co.uk", False, "placeholder", ["rates", "monetary_policy", "macro"]),
    _source("Euronext", "European Union", "Europe", "en,fr,nl,pt", "exchange", 0.93, "official", "public_web", "https://www.euronext.com", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Deutsche Boerse", "Germany", "Europe", "de,en", "exchange", 0.93, "official", "public_web", "https://www.deutsche-boerse.com", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("SIX Swiss Exchange", "Switzerland", "Europe", "de,fr,it,en", "exchange", 0.92, "official", "public_web", "https://www.six-group.com", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Borsa Italiana", "Italy", "Europe", "it,en", "exchange", 0.91, "official", "public_web", "https://www.borsaitaliana.it", False, "placeholder", ["listing", "announcements", "market_data"]),
    # Americas
    _source("Yahoo Finance", "United States", "Global", "en", "market_data", 0.88, "near_realtime", "public_package", "https://finance.yahoo.com", False, "active", ["quote", "index", "summary"]),
    _source("Finnhub", "United States", "Global", "en", "market_data_news", 0.84, "near_realtime", "authorized_api", "https://finnhub.io", True, "active" if settings.finnhub_api_key else "requires_api_key", ["news", "fundamentals", "quote"], "Active Finnhub adapter requires FINNHUB_API_KEY."),
    _source("FRED", "United States", "Americas", "en", "macro", 0.93, "official", "authorized_api", "https://fred.stlouisfed.org", True, _credential_status("FRED_API_KEY"), ["rates", "inflation", "employment"], "Active FRED adapter requires FRED_API_KEY."),
    _source("SEC EDGAR", "United States", "Americas", "en", "regulator", 0.96, "official", "public_api", "https://www.sec.gov/edgar", False, "placeholder", ["filings", "disclosure"]),
    _source("Nasdaq", "United States", "Americas", "en", "exchange", 0.92, "near_realtime", "public_web", "https://www.nasdaq.com", False, "placeholder", ["quote", "listing", "market_data"]),
    _source("NYSE", "United States", "Americas", "en", "exchange", 0.93, "near_realtime", "public_web", "https://www.nyse.com", False, "placeholder", ["quote", "listing", "market_data"]),
    _source("CME Group", "United States", "Americas", "en", "exchange", 0.92, "near_realtime", "public_web", "https://www.cmegroup.com", False, "placeholder", ["futures", "commodities", "rates"]),
    _source("U.S. Bureau of Labor Statistics", "United States", "Americas", "en", "macro", 0.95, "official", "public_api", "https://www.bls.gov", False, "placeholder", ["employment", "inflation", "macro"]),
    _source("U.S. Bureau of Economic Analysis", "United States", "Americas", "en", "macro", 0.95, "official", "public_api", "https://www.bea.gov", False, "placeholder", ["gdp", "income", "macro"]),
    _source("TMX Money", "Canada", "Americas", "en,fr", "market_data", 0.89, "delayed", "public_web", "https://money.tmx.com", False, "placeholder", ["quote", "listing", "market_data"]),
    _source("B3", "Brazil", "Americas", "pt,en", "exchange", 0.91, "official", "public_web", "https://www.b3.com.br", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Banco de Mexico", "Mexico", "Americas", "es,en", "central_bank", 0.94, "official", "public_api", "https://www.banxico.org.mx", False, "placeholder", ["rates", "fx", "macro"]),
    # Middle East
    _source("Saudi Exchange", "Saudi Arabia", "Middle East", "ar,en", "exchange", 0.92, "official", "public_web", "https://www.saudiexchange.sa", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Dubai Financial Market", "United Arab Emirates", "Middle East", "ar,en", "exchange", 0.91, "official", "public_web", "https://www.dfm.ae", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Abu Dhabi Securities Exchange", "United Arab Emirates", "Middle East", "ar,en", "exchange", 0.91, "official", "public_web", "https://www.adx.ae", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Qatar Stock Exchange", "Qatar", "Middle East", "ar,en", "exchange", 0.90, "official", "public_web", "https://www.qe.com.qa", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Boursa Kuwait", "Kuwait", "Middle East", "ar,en", "exchange", 0.90, "official", "public_web", "https://www.boursakuwait.com.kw", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Tel Aviv Stock Exchange", "Israel", "Middle East", "he,en", "exchange", 0.90, "official", "public_web", "https://www.tase.co.il/en", False, "placeholder", ["listing", "announcements", "market_data"]),
    # Africa
    _source("Johannesburg Stock Exchange", "South Africa", "Africa", "en", "exchange", 0.91, "official", "public_web", "https://www.jse.co.za", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Nigerian Exchange Group", "Nigeria", "Africa", "en", "exchange", 0.90, "official", "public_web", "https://ngxgroup.com", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Egyptian Exchange", "Egypt", "Africa", "ar,en", "exchange", 0.89, "official", "public_web", "https://www.egx.com.eg", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Nairobi Securities Exchange", "Kenya", "Africa", "en", "exchange", 0.88, "official", "public_web", "https://www.nse.co.ke", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("BRVM", "West Africa", "Africa", "fr,en", "exchange", 0.88, "official", "public_web", "https://www.brvm.org", False, "placeholder", ["listing", "announcements", "market_data"]),
    _source("Bank of Ghana", "Ghana", "Africa", "en", "central_bank", 0.90, "official", "public_web", "https://www.bog.gov.gh", False, "placeholder", ["rates", "fx", "macro"]),
    # Global
    _source("World Bank", "Global", "Global", "en", "macro", 0.94, "official", "public_api", "https://data.worldbank.org", False, "active", ["macro", "country_indicators"]),
    _source("IMF", "Global", "Global", "en", "macro", 0.94, "official", "public_api", "https://www.imf.org", False, "active", ["macro", "financial_statistics"]),
    _source("Reuters", "Global", "Global", "en", "news", 0.91, "latest", "public_web", "https://www.reuters.com", False, "placeholder", ["news"]),
    _source("Bloomberg", "Global", "Global", "en", "news_market", 0.90, "latest", "public_web", "https://www.bloomberg.com", False, "placeholder", ["news", "market_data"]),
    _source("CNBC", "Global", "Global", "en", "news", 0.82, "latest", "public_web", "https://www.cnbc.com", False, "placeholder", ["news"]),
    _source("Investing.com", "Global", "Global", "en", "market_data", 0.78, "near_realtime", "public_web", "https://www.investing.com", False, "placeholder", ["quote", "calendar"]),
    _source("TradingView", "Global", "Global", "en", "market_data", 0.80, "near_realtime", "public_web", "https://www.tradingview.com", False, "placeholder", ["quote", "technical"]),
    _source("OECD Data", "Global", "Global", "en,fr", "macro", 0.93, "official", "public_api", "https://data.oecd.org", False, "placeholder", ["macro", "country_indicators"]),
    _source("Bank for International Settlements", "Global", "Global", "en", "macro", 0.94, "official", "public_api", "https://www.bis.org", False, "placeholder", ["rates", "banking", "macro"]),
]


def list_sources() -> list[dict]:
    return [source.to_dict() for source in SOURCES]


def list_source_objects() -> list[FinancialSource]:
    return list(SOURCES)


def group_sources_by_region() -> dict[str, list[dict]]:
    grouped = {region: [] for region in REGION_GROUPS}
    for source in SOURCES:
        grouped.setdefault(source.region, []).append(source.to_dict())
    return grouped


def sources_by_region(region: str) -> list[dict]:
    normalized = region.strip().lower().replace("-", " ")
    return [
        source.to_dict()
        for source in SOURCES
        if source.region.lower() == normalized
    ]


def sources_by_country(country: str) -> list[dict]:
    normalized = country.strip().lower()
    return [
        source.to_dict()
        for source in SOURCES
        if source.country.lower() == normalized
    ]


def source_status() -> dict[str, str]:
    return {source.name: source.status for source in SOURCES}


def source_status_summary() -> dict:
    statuses = {"active": 0, "placeholder": 0, "unavailable": 0, "requires_api_key": 0}
    for source in SOURCES:
        statuses[source.status] += 1

    requiring_api_keys = [source.name for source in SOURCES if source.requires_api_key]
    active_sources = [source.name for source in SOURCES if source.status == "active"]
    placeholder_sources = [source.name for source in SOURCES if source.status == "placeholder"]
    unavailable_sources = [source.name for source in SOURCES if source.status == "unavailable"]

    return {
        "total_sources": len(SOURCES),
        "active_sources": len(active_sources),
        "placeholder_sources": len(placeholder_sources),
        "unavailable_sources": len(unavailable_sources),
        "sources_requiring_api_keys": len(requiring_api_keys),
        "status_counts": statuses,
        "active": active_sources,
        "placeholder": placeholder_sources,
        "unavailable": unavailable_sources,
        "requires_api_key": requiring_api_keys,
    }


def get_source(name: str) -> FinancialSource | None:
    lowered = name.lower()
    return next((source for source in SOURCES if source.name.lower() == lowered), None)


def reliability_for(name: str | None) -> float:
    source = get_source(name or "")
    return source.reliability_score if source else 0.55


def sources_for(data_types: set[str], region: str | None = None) -> list[FinancialSource]:
    selected = []
    for source in SOURCES:
        if region and source.region.lower() != region.lower():
            continue
        if data_types.intersection(source.data_types) or source.source_type in data_types:
            selected.append(source)
    return sorted(selected, key=lambda item: item.reliability_score, reverse=True)
