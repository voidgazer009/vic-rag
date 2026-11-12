"""Language-aware tokenization that works for Chinese, English and mixed text
without any external dependency.

- Latin / digits: lowercase word tokens (keeps things like "cif", "40hq", "l/c" -> "l", "c").
- CJK: character unigrams + bigrams, the standard dictionary-free approach that
  makes BM25 work well on Chinese.
"""
from __future__ import annotations

import re
import unicodedata

_CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_TOKEN_RE = re.compile(rf"[{_CJK}]+|[a-z0-9]+(?:[.\-][a-z0-9]+)*")

STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "is", "are", "be",
    "with", "by", "as", "at", "it", "this", "that", "what", "how", "which", "do", "does",
    "的", "了", "是", "在", "和", "与", "及", "或", "吗", "呢", "啊", "吧", "么", "什", "怎",
}


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for m in _TOKEN_RE.finditer(normalize(text)):
        tok = m.group(0)
        if re.match(rf"[{_CJK}]", tok):
            chars = [c for c in tok]
            out.extend(c for c in chars if c not in STOPWORDS)
            out.extend(chars[i] + chars[i + 1] for i in range(len(chars) - 1))
        else:
            if tok not in STOPWORDS:
                out.append(tok)
            if "-" in tok or "." in tok:
                out.extend(p for p in re.split(r"[.\-]", tok) if p and p not in STOPWORDS)
    return out


def count_units(text: str) -> int:
    """Rough length unit: 1 per CJK char, 1 per latin word (close to token cost)."""
    cjk = len(re.findall(rf"[{_CJK}]", text))
    words = len(re.findall(r"[A-Za-z0-9]+", text))
    return cjk + words
