"""Title analyzer — niche detection, keyword extraction, sentiment scoring."""
from __future__ import annotations

import re
from dataclasses import dataclass

NICHE_KEYWORDS = {
    "ai_tech": ["ai", "gpt", "chatgpt", "claude", "llm", "neural", "agent", "model",
                "automation", "robot", "tech", "code", "coding", "developer", "openai",
                "anthropic", "google", "nvidia", "compute"],
    "crime_documentary": ["crime", "murder", "killer", "fraud", "scam", "case", "mystery",
                          "investigation", "detective", "fbi", "cia", "police", "stolen",
                          "missing", "hacker", "hacked", "cyber", "leaked"],
    "finance_money": ["money", "stock", "invest", "billion", "million", "trillion", "bank",
                      "wealth", "rich", "broke", "salary", "economy", "recession", "inflation",
                      "crypto", "bitcoin", "hedge fund", "ceo", "fed"],
    "documentary_essay": ["history", "documentary", "story", "explained", "why", "how",
                          "fall", "rise", "empire", "war", "civilization", "culture"],
}

SHOCK_WORDS = {"secret", "nobody", "illegal", "banned", "truth", "exposed", "worst",
               "insane", "dead", "crisis", "lying", "hidden", "shocking", "warning",
               "destroyed", "ruined", "collapse"}

NEGATIVE_WORDS = {"die", "dying", "fail", "failed", "broke", "lost", "wrong",
                  "bad", "worst", "scam", "lie", "fake", "stolen", "destroyed",
                  "ruined", "hacked", "killed", "missing", "fraud"}


@dataclass
class TitleAnalysis:
    title: str
    niche: str
    keywords: list[str]
    numbers: list[str]
    money: list[str]
    shock_words: list[str]
    word_count: int
    char_count: int
    sentiment: str           # negative / neutral / positive
    emotion: str             # urgent / curious / tense / informational

    def to_dict(self) -> dict:
        return self.__dict__


def detect_niche(title: str) -> str:
    t = title.lower()
    scores: dict[str, int] = {}
    for niche, words in NICHE_KEYWORDS.items():
        scores[niche] = sum(1 for w in words if w in t)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "documentary_essay"


def extract_money(text: str) -> list[str]:
    return re.findall(r"\$\s?\d+[\d,\.]*\s?[KMBkmb]?(?:illion|illions)?", text)


def extract_numbers(text: str) -> list[str]:
    nums = re.findall(r"\b\d+[\d,\.]*[KMBkmb%]?\b", text)
    return nums


def analyze_title(title: str) -> TitleAnalysis:
    t = title.lower()
    words = title.split()
    money = extract_money(title)
    nums = [n for n in extract_numbers(title) if n not in "".join(money)]
    shock = [w for w in SHOCK_WORDS if w in t]
    neg = sum(1 for w in NEGATIVE_WORDS if w in t)

    sentiment = "negative" if neg >= 1 else "neutral"
    emotion = "urgent" if shock or neg >= 2 else (
        "curious" if title.lower().startswith(("why", "how", "what")) else "informational"
    )

    keywords = [w.lower() for w in words
                if len(w) > 3 and w.lower() not in {"that", "this", "with", "from", "your"}]

    return TitleAnalysis(
        title=title,
        niche=detect_niche(title),
        keywords=keywords[:8],
        numbers=nums,
        money=money,
        shock_words=shock,
        word_count=len(words),
        char_count=len(title),
        sentiment=sentiment,
        emotion=emotion,
    )
