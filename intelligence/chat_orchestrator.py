import logging
from typing import Any

from llm.provider import LLMProvider
from rag.pipeline import FinancialRAGPipeline
from retrieval.retriever import detect_symbols
from tools.market_tools import get_market_index_context

from .intent_router import intent_classifier
from .response_formatter import local_finance_answer, news_answer_from_retrieval
from .tool_selector import ToolSelector


logger = logging.getLogger(__name__)


async def generate_intelligent_reply(message: str, history: list[Any] | None = None) -> dict[str, Any]:
    intent = intent_classifier(message)
    symbols = detect_symbols(message)
    llm = LLMProvider()
    selection = ToolSelector().select(intent, has_symbols=bool(symbols), llm_configured=llm.is_configured)

    logger.info("Selected intelligence tool=%s intent=%s message=%r", selection.name, intent, message[:160])

    if selection.name == "market_index_tool":
        return await get_market_index_context(message)

    if selection.name == "financial_rag_pipeline":
        return await FinancialRAGPipeline().run(message, use_llm=selection.use_llm)

    if selection.name == "news_rag_pipeline":
        pipeline_result = await FinancialRAGPipeline().run(message, use_llm=False)
        pipeline_result["answer"] = news_answer_from_retrieval(message, pipeline_result.get("retrieval", {}))
        return pipeline_result

    return await general_finance_chat(message, intent, history, llm)


async def general_finance_chat(
    message: str,
    intent: str,
    history: list[Any] | None = None,
    llm: LLMProvider | None = None,
) -> dict[str, Any]:
    fallback = local_finance_answer(message, intent)
    system = (
        "Bạn là trợ lý AI tài chính nói tiếng Việt tự nhiên. Trả lời linh hoạt, có tính giáo dục, "
        "không bịa số liệu thị trường, không đưa khuyến nghị đầu tư cá nhân. "
        "Nếu thiếu dữ liệu thị trường, hãy trả lời theo hướng giáo dục thay vì chỉ yêu cầu người dùng cung cấp mã. "
        "Cấu trúc câu trả lời bằng các phần: Tóm tắt, Dữ liệu, Phân tích, Rủi ro, Kết luận. "
        "Không lặp lại nguyên văn fallback hoặc một đoạn nhiều lần."
    )
    history_text = "\n".join(
        f"{getattr(item, 'role', 'user')}: {getattr(item, 'content', '')}" for item in (history or [])[-6:]
    )
    provider = llm or LLMProvider()
    answer = await provider.complete(
        system,
        f"Lịch sử gần đây:\n{history_text}\n\nCâu hỏi hiện tại: {message}",
        fallback,
        temperature=0.45,
    )
    return {
        "answer": answer,
        "analysis": {"intent": intent, "mode": "general_finance_chat"},
        "retrieval": {"intent": intent, "symbols": [], "bundles": []},
        "citations": [],
        "market_data": [],
    }
