from fastapi import APIRouter

from retrieval.global_source_registry import (
    group_sources_by_region,
    list_sources,
    source_status,
    source_status_summary,
    sources_by_country,
    sources_by_region,
)


router = APIRouter(tags=["sources"])


@router.get("/sources")
async def sources():
    return {"sources": list_sources()}


@router.get("/sources/all")
async def all_sources():
    return {
        "total_sources": len(list_sources()),
        "groups": group_sources_by_region(),
    }


@router.get("/sources/by-region/{region}")
async def sources_for_region(region: str):
    return {"region": region, "sources": sources_by_region(region)}


@router.get("/sources/by-country/{country}")
async def sources_for_country(country: str):
    return {"country": country, "sources": sources_by_country(country)}


@router.get("/sources/status")
async def sources_status():
    return {
        "source_status": source_status(),
        "summary": source_status_summary(),
    }
