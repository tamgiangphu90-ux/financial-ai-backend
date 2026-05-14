from typing import Any


class PatternLearning:
    def detect_repeated_questions(self, messages: list[dict[str, Any]]) -> list[str]:
        seen: dict[str, int] = {}
        for item in messages:
            key = " ".join(str(item.get("content", "")).lower().split())[:160]
            if key:
                seen[key] = seen.get(key, 0) + 1
        return [question for question, count in seen.items() if count > 1]
