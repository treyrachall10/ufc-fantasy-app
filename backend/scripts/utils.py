import re
import unicodedata

def normalize_name(name):
    """
        -   Normalizes name for easier database lookups
        -   RETURNS: normalized name; no special characters; no capitals
    """
    if not name:
        return None

    # Base normalization
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = re.sub(r"[-’'.]", " ", name)   # remove punctuation
    name = re.sub(r"\s+", " ", name)      # collapse spaces
    name = name.strip()

    # Known aliases / canonical mappings (ONLY edge cases)
    ALIASES = {
        "zachary reese": "zach reese",
        "montserrat rendon": "montse rendon",
        "rafael cerqueira": "rafael cerquiera",
        "michael aswell": "michael aswell jr",
        "jose medina": "jose daniel medina"
    }

    return ALIASES.get(name, name)