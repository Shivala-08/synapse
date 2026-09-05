"""Entity extraction using regex and spaCy.

Extracts domain-specific entities from text. Supports wikilink parsing
for Obsidian-style [[Note Name]] syntax when the domain profile requests it.
"""

import re
from typing import Optional
from loguru import logger


# --- Wikilink pattern (Obsidian-style [[Note Name]] syntax) ---
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")


def extract_wikilinks(text: str) -> list[str]:
    """Return note names from [[Note Name]] or [[Note Name|alias]] syntax."""
    return [m.strip() for m in WIKILINK_PATTERN.findall(text)]


# --- Regex patterns for domain-specific entities ---

# Equipment tags: EQ-1001, PUMP-A01, COMP-C01, HX-D01, VAN-V01, TNK-T01, FIL-F01, MTR-M01
EQUIPMENT_TAG_PATTERN = re.compile(
    r'\b((?:EQ|PUMP|COMP|HX|VAN|VAL|TNK|FIL|MTR)-[A-Z]?\d{2,4})\b',
    re.IGNORECASE,
)

# Permit IDs: PRM-2026-5001
PERMIT_ID_PATTERN = re.compile(
    r'\b(PRM-\d{4}-\d{4})\b',
    re.IGNORECASE,
)

# Work order IDs: WO-2026-1001
WORK_ORDER_ID_PATTERN = re.compile(
    r'\b(WO-\d{4}-\d{4})\b',
    re.IGNORECASE,
)

# Incident IDs: INC-2026-9001
INCIDENT_ID_PATTERN = re.compile(
    r'\b(INC-\d{4}-\d{4})\b',
    re.IGNORECASE,
)

# Inspection IDs: INS-2026-8001
INSPECTION_ID_PATTERN = re.compile(
    r'\b(INS-\d{4}-\d{4})\b',
    re.IGNORECASE,
)

# Regulation references: OISD-116, DGMS Circular 2023-01, Factory Act Section 7A, Section 36
REGULATION_PATTERNS = [
    re.compile(r'\b(OISD(?:\s*[\-\–\—\─]\s*(?:GDN-|STD-|GDN|STD)?\s*[\-\–\—\─]?\s*)?\d{2,3})\b', re.IGNORECASE),
    re.compile(r'\b(DGMS(?:\s+(?:Circular|Technical\s+Circular))?\s+\d{4}-\d{2})\b', re.IGNORECASE),
    re.compile(r'\b(DGMS\s+Technical\s+Circular\s+\d+)\b', re.IGNORECASE),
    re.compile(r'\b(Factory\s+Act\s+Section\s+\d+[A-Z]?)\b', re.IGNORECASE),
    re.compile(r'\b(Section\s+\d+[A-Z]?)\b', re.IGNORECASE),
]

# Plant names
PLANT_PATTERNS = [
    re.compile(r'\b(Refinery\s+Unit\s+[A-Z])\b', re.IGNORECASE),
    re.compile(r'\b(Power\s+Plant\s+[A-Z])\b', re.IGNORECASE),
    re.compile(r'\b(Chemical\s+Plant\s+[A-Z])\b', re.IGNORECASE),
    re.compile(r'\b(Steel\s+Mill\s+[A-Z])\b', re.IGNORECASE),
]

# Hazard types
HAZARD_PATTERNS = [
    re.compile(r'\b(Fire\s+hazard)\b', re.IGNORECASE),
    re.compile(r'\b(Confined\s+space)\b', re.IGNORECASE),
    re.compile(r'\b(Working\s+at\s+height)\b', re.IGNORECASE),
    re.compile(r'\b(Electrical)\b', re.IGNORECASE),
    re.compile(r'\b(Chemical\s+exposure)\b', re.IGNORECASE),
    re.compile(r'\b(Noise)\b', re.IGNORECASE),
    re.compile(r'\b(Falling\s+objects)\b', re.IGNORECASE),
]

# Incident types
INCIDENT_TYPE_PATTERNS = [
    re.compile(r'\b(Near\s+Miss)\b', re.IGNORECASE),
    re.compile(r'\b(First\s+Aid)\b', re.IGNORECASE),
    re.compile(r'\b(Recordable)\b', re.IGNORECASE),
    re.compile(r'\b(Lost\s+Time)\b', re.IGNORECASE),
]

# Permit types
PERMIT_TYPE_PATTERNS = [
    re.compile(r'\b(Hot\s+Work)\b', re.IGNORECASE),
    re.compile(r'\b(Confined\s+Space\s+Entry)\b', re.IGNORECASE),
    re.compile(r'\b(Work\s+at\s+Height)\b', re.IGNORECASE),
    re.compile(r'\b(Electrical\s+Isolation)\b', re.IGNORECASE),
    re.compile(r'\b(Line\s+Breaking)\b', re.IGNORECASE),
    re.compile(r'\b(Excavation)\b', re.IGNORECASE),
]


# ── spaCy PERSON/ORG junk filter ──────────────────────────────────────────────
# spaCy frequently mislabels PDF-extracted fragments (roman numerals, single
# letters, lowercase headings) as PERSON/ORG. These heuristics reject that junk
# while keeping genuine capitalized names and organisations.

_ROMAN_NUMERAL_RE = re.compile(
    r"^(?=[MDCLXVI])M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE,
)

# Symbols/punctuation that indicate fragments ("red &", "the ( h )")
_JUNK_CHAR_RE = re.compile(r"[^a-zA-Z\s'.-]")

# Single-letter tokens ("b. gate", "w. r. t. sea") — initials like "John Q. Public"
# are rare in this domain and acceptable to drop
_SINGLE_LETTER_TOKEN_RE = re.compile(r"(?<![a-zA-Z])[a-zA-Z](?![a-zA-Z])")

# Column/address fragments that spaCy glues onto names ("Anthony Knoll Apt",
# "Expiry Date", "Christian Vaughn Issue")
_JUNK_WORDS = frozenset({
    "apt", "md", "phd", "dept", "department", "requested", "issued", "issue",
    "expiry", "completion", "inspection", "date", "box", "floor", "ste",
    "contact", "tag", "address", "chemical",
})


def is_valid_person_entity(text: str) -> bool:
    """Return True if a spaCy PERSON/ORG span looks like a real entity.

    Rejects roman numerals, digit-laden fragments, single letters, heavy
    punctuation/symbols, all-lowercase fragments, and column-spanning spans
    that spaCy commonly mislabels as people/organisations in PDF/CSV text.
    """
    raw = text
    # Collapse all whitespace (incl. newlines) before validating
    t = " ".join(raw.split())

    # Spans that cross a line break are almost always column-spanning junk
    # ("Alexandra Taylor\nDepartment"), unless they are just a name with a
    # trailing newline artifact ("Diane Miller\n" -> "Diane Miller").
    if "\n" in raw or "\t" in raw:
        if len(re.findall(r"[a-zA-Z]+", t)) > 2:
            return False

    if not t or len(t) < 2:
        return False
    if _ROMAN_NUMERAL_RE.match(t):
        return False
    if re.search(r"\d", t):
        return False
    if len(_JUNK_CHAR_RE.findall(t)) > 1:
        return False
    if _SINGLE_LETTER_TOKEN_RE.search(t):
        return False
    letters = re.findall(r"[a-zA-Z]+", t)
    if not letters:
        return False
    # State-code abbreviations ("AP", "AZ")
    if len(letters) == 1 and len(letters[0]) <= 2 and letters[0].isupper():
        return False
    # All-lowercase fragments ("gb", "the united nations", "acetylene cylinder")
    if all(w.islower() for w in letters):
        return False
    # Column/address fragments ("Anthony Knoll Apt", "Expiry Date", "Chemical")
    if any(w.lower() in _JUNK_WORDS for w in letters):
        return False
    return True


class EntityExtractor:
    """Extracts industrial entities from text using spaCy and regex patterns."""

    def __init__(self):
        self.nlp = None
        self.spacy_available = False
        try:
            import spacy
            from src.config import settings
            model_name = getattr(settings, "spacy_model", "en_core_web_sm")
            logger.info(f"Loading spaCy model for NER: {model_name}")
            self.nlp = spacy.load(model_name)
            self.spacy_available = True
            logger.info("spaCy model loaded successfully.")
        except Exception as e:
            logger.warning(f"spaCy not available or failed to load: {e}. Falling back to pure regex.")

    def extract_all(self, text: str, metadata: Optional[dict] = None, domain_profile=None) -> dict:
        """Extract all entity types from text.

        When domain_profile is given and link_syntax == "wikilink", also
        extracts [[Note Name]] references and adds them as wikilink entities.
        """
        metadata = metadata or {}
        spacy_entities = []

        # 1. Try to extract entities using spaCy
        if self.spacy_available and self.nlp:
            try:
                doc = self.nlp(text[:50000])  # limit length to avoid memory spikes
                for ent in doc.ents:
                    if ent.label_ in ("PERSON", "ORG"):
                        entity_text = " ".join(ent.text.split())  # normalize whitespace
                        if is_valid_person_entity(entity_text):
                            spacy_entities.append(entity_text)
            except Exception as e:
                logger.error(f"spaCy NER extraction failed: {e}")

        # 2. Extract domain entities using custom regexes
        entities = {
            "equipment": sorted(set(self._extract_equipment(text, metadata))),
            "permits": sorted(set(self._extract_permits(text, metadata))),
            "work_orders": sorted(set(self._extract_work_orders(text, metadata))),
            "incidents": sorted(set(self._extract_incidents(text, metadata))),
            "inspections": sorted(set(self._extract_inspections(text, metadata))),
            "regulations": sorted(set(self._extract_regulations(text, metadata))),
            "plants": sorted(set(self._extract_plants(text, metadata))),
            "hazards": sorted(set(self._extract_hazards(text, metadata))),
            "incident_types": sorted(set(self._extract_incident_types(text, metadata))),
            "permit_types": sorted(set(self._extract_permit_types(text, metadata))),
            "personnel": sorted(set(spacy_entities)) if spacy_entities else [],
        }

        # Query-side regex fallback logic: if spaCy returned 0 entities, fallback/ensure regex is populated
        if not spacy_entities:
            logger.debug("spaCy returned 0 entities. Relying on query-side regex fallback.")
            entities["personnel"] = sorted(set(self._extract_personnel(text)))

        # 3. Wikilink extraction (gated on domain profile)
        entities["wikilinks"] = []
        if domain_profile and getattr(domain_profile, "link_syntax", "none") == "wikilink":
            links = extract_wikilinks(text)
            entities["wikilinks"] = sorted(set(links))
            if links:
                logger.debug(f"Extracted {len(entities['wikilinks'])} wikilinks from text")

        # Count total
        total = sum(len(v) for v in entities.values())
        logger.debug(f"Extracted {total} entities from text ({len(text)} chars)")
        return entities

    def _extract_equipment(self, text: str, metadata: dict) -> list[str]:
        """Extract equipment tags from text and metadata."""
        tags = set()
        # From regex
        for match in EQUIPMENT_TAG_PATTERN.finditer(text):
            tags.add(match.group(1).upper())
        # From metadata
        eq = metadata.get("equipment_tag", "")
        if eq:
            tags.add(eq.upper())
        return list(tags)

    def _extract_permits(self, text: str, metadata: dict) -> list[str]:
        """Extract permit IDs."""
        ids = set()
        for match in PERMIT_ID_PATTERN.finditer(text):
            ids.add(match.group(1).upper())
        pid = metadata.get("permit_id", "")
        if pid:
            ids.add(pid.upper())
        return list(ids)

    def _extract_work_orders(self, text: str, metadata: dict) -> list[str]:
        """Extract work order IDs."""
        ids = set()
        for match in WORK_ORDER_ID_PATTERN.finditer(text):
            ids.add(match.group(1).upper())
        wid = metadata.get("work_order_id", "")
        if wid:
            ids.add(wid.upper())
        return list(ids)

    def _extract_incidents(self, text: str, metadata: dict) -> list[str]:
        """Extract incident report IDs."""
        ids = set()
        for match in INCIDENT_ID_PATTERN.finditer(text):
            ids.add(match.group(1).upper())
        iid = metadata.get("incident_id", "")
        if iid:
            ids.add(iid.upper())
        return list(ids)

    def _extract_inspections(self, text: str, metadata: dict) -> list[str]:
        """Extract inspection IDs."""
        ids = set()
        for match in INSPECTION_ID_PATTERN.finditer(text):
            ids.add(match.group(1).upper())
        iid = metadata.get("inspection_id", "")
        if iid:
            ids.add(iid.upper())
        return list(ids)

    def _extract_regulations(self, text: str, metadata: dict) -> list[str]:
        """Extract regulation references."""
        refs = set()
        for pattern in REGULATION_PATTERNS:
            for match in pattern.finditer(text):
                refs.add(match.group(1))
        ref = metadata.get("regulation_ref", "")
        if ref:
            refs.add(ref)
        return list(refs)

    def _extract_plants(self, text: str, metadata: dict) -> list[str]:
        """Extract plant names."""
        plants = set()
        for pattern in PLANT_PATTERNS:
            for match in pattern.finditer(text):
                plants.add(match.group(1))
        plant = metadata.get("plant", "")
        if plant:
            plants.add(plant)
        return list(plants)

    def _extract_hazards(self, text: str, metadata: dict) -> list[str]:
        """Extract hazard types."""
        hazards = set()
        for pattern in HAZARD_PATTERNS:
            for match in pattern.finditer(text):
                hazards.add(match.group(1))
        return list(hazards)

    def _extract_incident_types(self, text: str, metadata: dict) -> list[str]:
        """Extract incident types."""
        types = set()
        for pattern in INCIDENT_TYPE_PATTERNS:
            for match in pattern.finditer(text):
                types.add(match.group(1))
        it = metadata.get("incident_type", "")
        if it:
            types.add(it)
        return list(types)

    def _extract_permit_types(self, text: str, metadata: dict) -> list[str]:
        """Extract permit types."""
        types = set()
        for pattern in PERMIT_TYPE_PATTERNS:
            for match in pattern.finditer(text):
                types.add(match.group(1))
        pt = metadata.get("permit_type", "")
        if pt:
            types.add(pt)
        return list(types)

    def _extract_personnel(self, text: str) -> list[str]:
        """Extract person names (fallback regex)."""
        pattern = re.compile(r'\b(?:Mr\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b')
        names = []
        for match in pattern.finditer(text):
            names.append(match.group(1))
        return names


# Module-level singleton
_default_extractor = None


def get_extractor() -> EntityExtractor:
    """Get or create the singleton entity extractor."""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = EntityExtractor()
    return _default_extractor


def extract_entities(text: str, metadata: Optional[dict] = None, domain_profile=None) -> dict:
    """Convenience function to extract entities from text."""
    return get_extractor().extract_all(text, metadata, domain_profile=domain_profile)
