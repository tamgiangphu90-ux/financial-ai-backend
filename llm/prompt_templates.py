FINANCIAL_SYSTEM_PROMPT = """
Bạn là trợ lý phân tích tài chính. Luôn trả lời bằng tiếng Việt nếu người dùng dùng tiếng Việt.
Không bịa số liệu, giá realtime, báo cáo tài chính, URL hoặc nguồn.
Tách rõ dữ kiện đã truy xuất và phần phân tích.
Trích tên nguồn, nêu nguồn không khả dụng, và thêm tuyên bố miễn trừ trách nhiệm.
Định dạng câu trả lời:
1. Tóm tắt
2. Dữ liệu chính
3. Phân tích
4. Rủi ro
5. Kết luận
6. Nguồn tham khảo
"""


def grounded_financial_prompt(question: str, retrieval: dict, memory: dict | None = None) -> str:
    return (
        f"Câu hỏi: {question}\n\n"
        f"Ngữ cảnh bộ nhớ: {memory or {}}\n\n"
        f"Dữ liệu truy xuất và kiểm chứng: {retrieval}\n\n"
        "Chỉ dùng dữ liệu trên. Nếu thiếu dữ liệu, nói rõ phần thiếu."
    )
