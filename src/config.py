"""
Configuration: lexicons, regex patterns, constants.

All lexicons are stored lowercase + accent-stripped for consistent matching.
The normalization function (preprocess.py) does the same on input text. (Basically strip accents and stuff before comparing)
"""

# ---------------------------------------------------------------------
# Colors (What is seen with the eye)
# ---------------------------------------------------------------------
# Simple hues (visual colors) + common furniture finishes
# Convention: wood tones (chêne, noyer, sonoma) count as colors
# because the furniture industry labels them that way (Amazon.fr, etc.)
# ---------------------------------------------------------------------
COLORS = {
    # Simple hues
    "blanc", "noir", "gris", "marron", "brun", "beige", "bleu", "vert",
    "rouge", "rose", "jaune", "orange", "violet", "pourpre", "turquoise",
    "anthracite", "taupe", "ivoire", "creme", "ocre", "bordeaux",
    # Metallic / special
    "dore", "argente", "cuivre", "bronze", "chrome", "transparent",
    # Wood tones (industry convention: they act as color labels)
    "chene", "noyer", "sonoma", "erable", "hetre", "pin", "acacia",
    "bambou", "teck", "wenge", "merisier", "frene",
}

# Multi-word color phrases (must be checked BEFORE single words)
COLOR_PHRASES = {
    "gris anthracite",
    "blanc casse",
    "blanc brillant",
    "noir brillant",
    "bois naturel",
    "bois clair",
    "bois fonce",
    "effet bois",
    "vert sauge",
    "bleu nuit",
    "bleu marine",
    "rose pale",
    "gris clair",
    "gris fonce",
}

# ---------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------
MATERIALS = {
    "bois", "metal", "verre", "acier", "aluminium", "plastique",
    "mdf", "pvc", "resine", "contreplaque", "agglomere", "melamine",
    "cuir", "simili", "velours", "coton", "lin", "polyester",
    "mousse", "latex", "ressort", "marbre", "granit", "ceramique",
    "tissu", "microfibre", "rotin", "osier", "textilene",
}

# Multi-word material phrases
MATERIAL_PHRASES = {
    "simili cuir",
    "bois massif",
    "bois d ingenieur",
    "panneau de particules",
    "acier inoxydable",
    "verre trempe",
}

# ---------------------------------------------------------------------
# Brands (stripped before matching, to avoid false hits)
# ---------------------------------------------------------------------
BRANDS = {
    "vasagle", "atmosphera", "homemania", "songmics", "vidaxl",
    "tectake", "giantex", "homcom", "ikea", "kartell", "yitahome",
    "klarfit", "decortie", "finebuy", "sklum", "mipan", "drawer",
    "noche", "frili", "pier", "import", "conforama", "but",
}

# ---------------------------------------------------------------------
# Dimension regex patterns
# ---------------------------------------------------------------------
# Ordered from MOST specific to LEAST specific.
# The extractor tries them in order and returns the first match.
#
# Notes:
# - Separators: x, X, ×, *
# - Decimal quirk: "33 6" means "33.6" (French comma lost in export)!!!
# - Numbers can be 1-3 digits
# - Unit "cm" is optional (but preferred)
# - "mm" is also possible
# ---------------------------------------------------------------------
# A number with optional French-decimal quirk: "33", "33 6" (=> 33.6)
_NUM = r"\d{1,3}(?:\s\d{1,2})?"

DIMENSION_PATTERNS = [
    # 1) Labeled 3D: L 110 x P 60 x H 36 cm
    (
        "labeled_3d",
        rf"\b[lL]\s*{_NUM}\s*[x×*]\s*[pP]\s*{_NUM}\s*[x×*]\s*[hH]\s*{_NUM}\s*(cm|mm)?\b",
    ),
    # 2) Plain 3D: 90x50x45 cm
    (
        "plain_3d",
        rf"\b{_NUM}\s*[x×*]\s*{_NUM}\s*[x×*]\s*{_NUM}\s*(cm|mm)?\b",
    ),
    # 3) Plain 2D: 140x190 cm
    (
        "plain_2d",
        rf"\b{_NUM}\s*[x×*]\s*{_NUM}\s*(cm|mm)?\b",
    ),
    # 4) Single: 80 cm  (only when followed by cm/mm to avoid "Lot de 2")
    (
        "single",
        rf"\b{_NUM}\s*(cm|mm)\b",
    ),
]

# ---------------------------------------------------------------------
# Dimension guards — phrases that LOOK like dimensions but aren't
# ---------------------------------------------------------------------
DIMENSION_FALSE_POSITIVES = {
    "usb 3 0", "usb 3.0", "usb3", "windows 10", "windows 11",
    "lot de 2", "lot de 3", "lot de 4", "lot de 5", "lot de 6",
    "set de 2", "set de 3", "set de 4",
    "3 tiroirs", "2 portes", "4 places", "5 niveaux", "3 niveaux",
}