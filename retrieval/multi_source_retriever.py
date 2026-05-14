from typing import Any

from filters.credibility_filter import apply_credibility_filter
from filters.duplicate_filter import remove_duplicates
from filters.freshness_filter import apply_freshness_filter
from filters.relevance_filter import apply_relevance_filter
from intelligence.query_planner import QueryPlan, build_query_plan
from retrieval.retriever import RetrievalEngine
from retrieval.source_ranker import rank_sources
from retrieval.source_verifier import verify_retrieval_bundle


class MultiSourceRetriever:
    def __init__(self) -> None:
        self.engine = RetrievalEngine()

    async def retrieve(self, message: str, plan: QueryPlan | None = None) -> dict[str, Any]:
        query_plan = plan or build_query_plan(message)
        retrieval = await self.engine.retrieve(message)

        for bundle in retrieval.get("bundles", []):
            quotes = bundle.get("quotes", [])
            news = bundle.get("news", [])
            quotes = apply_relevance_filter(quotes, message, [bundle.get("symbol", "")])
            quotes = remove_duplicates(apply_credibility_filter(quotes))
            news = apply_relevance_filter(news, message, [bundle.get("symbol", "")])
            news = remove_duplicates(apply_freshness_filter(apply_credibility_filter(news, minimum_score=0.5)))
            bundle["quotes"] = rank_sources(quotes)
            bundle["news"] = rank_sources(news)
            verify_retrieval_bundle(bundle)

        retrieval["query_plan"] = query_plan.to_dict()
        retrieval["source_status"] = self._source_status(retrieval)
        retrieval["confidence_score"] = self._confidence(retrieval)
        return retrieval

    def _source_status(self, retrieval: dict[str, Any]) -> dict[str, str]:
        status: dict[str, str] = {}
        plan_sources = (retrieval.get("query_plan") or {}).get("sources", [])
        for source in plan_sources:
            status[source] = "planned"
        for bundle in retrieval.get("bundles", []):
            for quote in bundle.get("quotes", []):
                if quote.get("source"):
                    status[quote["source"]] = "active"
            for item in bundle.get("news", []):
                if item.get("source"):
                    status[item["source"]] = "active"
            for error in bundle.get("errors", []):
                if error.get("source"):
                    status[error["source"]] = "unavailable"
        return status

    def _confidence(self, retrieval: dict[str, Any]) -> float:
        scores = []
        for bundle in retrieval.get("bundles", []):
            confidence = (bundle.get("verification") or {}).get("confidence")
            if confidence is not None:
                scores.append(float(confidence))
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 2)
