"""Task 2 — extract dimension, color, material from product titles."""
import re
from typing import Optional

from src.config import (
    COLORS, COLOR_PHRASES,
    MATERIALS, MATERIAL_PHRASES,
    DIMENSION_PATTERNS,
    DIMENSION_FALSE_POSITIVES,
)
from src.preprocess import normalize_for_matching, normalize_light


def _fix_decimal_quirk(match: str) -> str:
    """ 33 6 into 33.6 -> problem with french to english conversion"""
    return re.sub(r"(\d)\s(\d)", r"\1.\2", match)


def _normalize_dimension_string(raw_match) -> dict:
    """
    From a regex match, produce {"dimension": "...", "unit": "cm"|"mm"|None}.
    """

    raw = raw_match.group(0)
    unit = raw_match.group(1)  # "cm", "mm", or None

    s = raw.strip()
    s = re.sub(r"\s*(cm|mm)\b", "", s, flags=re.IGNORECASE) # remove units
    s = _fix_decimal_quirk(s)
    s = re.sub(r"\s*[x×*]\s*", "x", s, flags=re.IGNORECASE) #unify seperators
    s = re.sub(r"[lLpPhH]\s*", "", s)                       #remove L P H
    s = s.strip()

    return {"dimension": s, "unit": unit.lower() if unit else None}


def extract_dimension(title) -> Optional[dict]:
    """ Takes title (label) returns dimension string or None"""
    if title is None or not isinstance(title, str):
        return None
    text = normalize_light(title)   # use the light one for dimensions
    for _name, pattern in DIMENSION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return _normalize_dimension_string(match)
    return None


# Helpers \/\/

def _find_phrase_matches(text_norm: str, phrases: set) -> list:
    found = []
    for phrase in phrases:
        if re.search(rf"\b{re.escape(phrase)}", text_norm):
            found.append(phrase)
    return found


def _find_word_matches(text_norm: str, words: set) -> list:
    found = []
    for word in words:
        if re.search(rf"\b{re.escape(word)}", text_norm):
            found.append(word)
    return found


# Public Functions
def extract_colors(title) -> list:
    """
    Input: "Fauteuil patchwork bleu et gris"
    Output: ["bleu", "gris"]
    """
    if title is None or not isinstance(title, str):
        return []
    text = normalize_for_matching(title)
    phrases = _find_phrase_matches(text, COLOR_PHRASES)
    words = _find_word_matches(text, COLORS)


    seen = set()
    result = []

    # Deduplicating (remove duplicates)
    for c in phrases + words:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def extract_materials(title) -> list:
    """
    Input: "Canapé simili cuir noir"
    Output: ["simili cuir", "cuir"]
    """
    if title is None or not isinstance(title, str):
        return []
    text = normalize_for_matching(title)
    phrases = _find_phrase_matches(text, MATERIAL_PHRASES)
    words = _find_word_matches(text, MATERIALS)
    seen = set()
    result = []
    for m in phrases + words:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result