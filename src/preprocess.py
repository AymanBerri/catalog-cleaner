"""Text normalization helpers."""
import re
import unicodedata


def strip_accents(text: str) -> str:
    ''' remove accents '''
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_for_matching(text) -> str:
    """Lowercase + strip accents + remove punctuation. Canonical(standard) form for color/material lexicon matching."""
    if text is None or not isinstance(text, str):
        return ""
    text = text.lower()                         #lowercase
    text = strip_accents(text)                  #strip accents
    text = re.sub(r"[^a-z0-9]+", " ", text)     #
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_light(text) -> str:
    """Lowercase + collapse whitespace. Preserves digits, 'x', '×', '*', 'cm' for dimension matching."""
    if text is None or not isinstance(text, str):   # protect agains null or integer values
        return ""
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text