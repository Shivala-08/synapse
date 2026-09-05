"""Unit tests for src/pipeline/extractor.py (regex entity extraction).

Run: python -m pytest tests/test_extractor.py -q
"""

import pytest

from src.pipeline.extractor import EntityExtractor, extract_entities, is_valid_person_entity


@pytest.fixture(scope="module")
def regex_extractor():
    """An extractor with spaCy disabled so tests exercise the pure regex paths."""
    ex = object.__new__(EntityExtractor)
    ex.nlp = None
    ex.spacy_available = False
    return ex


def test_equipment_tags(regex_extractor):
    ents = regex_extractor.extract_all(
        "Pump PUMP-A01 failed. Check EQ-1001 and COMP-C01, TNK-T01, HX-D01."
    )
    equipment = ents["equipment"]
    assert "PUMP-A01" in equipment
    assert "EQ-1001" in equipment
    assert "COMP-C01" in equipment
    assert "TNK-T01" in equipment
    assert "HX-D01" in equipment


def test_equipment_tags_case_insensitive(regex_extractor):
    ents = regex_extractor.extract_all("valve van-v01 and filter fil-f01")
    assert "VAN-V01" in ents["equipment"]
    assert "FIL-F01" in ents["equipment"]


def test_domain_ids(regex_extractor):
    ents = regex_extractor.extract_all(
        "PRM-2026-5001 WO-2026-1001 INC-2026-9001 INS-2026-8001"
    )
    assert ents["permits"] == ["PRM-2026-5001"]
    assert ents["work_orders"] == ["WO-2026-1001"]
    assert ents["incidents"] == ["INC-2026-9001"]
    assert ents["inspections"] == ["INS-2026-8001"]


def test_regulations(regex_extractor):
    ents = regex_extractor.extract_all(
        "Per OISD-116, OISD-GDN-192, DGMS Circular 2023-01, "
        "Factory Act Section 7A and Section 36."
    )
    regs = ents["regulations"]
    assert "OISD-116" in regs
    assert "OISD-GDN-192" in regs
    assert "DGMS Circular 2023-01" in regs
    assert "Factory Act Section 7A" in regs
    assert "Section 36" in regs


def test_plants(regex_extractor):
    ents = regex_extractor.extract_all("Located at Refinery Unit A and Power Plant B")
    assert "Refinery Unit A" in ents["plants"]
    assert "Power Plant B" in ents["plants"]


def test_hazards_and_types(regex_extractor):
    ents = regex_extractor.extract_all(
        "Hot Work near a Fire hazard. Confined Space Entry requires a permit. Near Miss reported."
    )
    assert "Fire hazard" in ents["hazards"]
    assert "Confined Space" in ents["hazards"]  # regex preserves source casing
    assert "Hot Work" in ents["permit_types"]
    assert "Confined Space Entry" in ents["permit_types"]
    assert "Near Miss" in ents["incident_types"]


def test_personnel_fallback_regex(regex_extractor):
    """Regression test: _extract_personnel used to crash with AttributeError."""
    ents = regex_extractor.extract_all(
        "Mr. John Smith is the safety officer and Dr. Priya Rao approves permits."
    )
    assert "John Smith" in ents["personnel"]
    assert "Priya Rao" in ents["personnel"]


def test_metadata_entities(regex_extractor):
    ents = regex_extractor.extract_all(
        "some body text",
        {
            "equipment_tag": "EQ-1001",
            "permit_id": "PRM-2026-5000",
            "regulation_ref": "OISD-130",
            "plant": "Steel Mill D",
        },
    )
    assert "EQ-1001" in ents["equipment"]
    assert "PRM-2026-5000" in ents["permits"]
    assert "OISD-130" in ents["regulations"]
    assert "Steel Mill D" in ents["plants"]


def test_extract_entities_convenience():
    ents = extract_entities("EQ-1001 at Refinery Unit A")
    assert "EQ-1001" in ents["equipment"]
    assert "Refinery Unit A" in ents["plants"]


# ── spaCy junk entity filter ──────────────────────────────────────────────────

@pytest.mark.parametrize("junk", [
    "vii", "viii", "xiii", "xviii", "xxiv", "xxxiv",  # roman numerals
    "349th", "section 2",                                # digits
    "gb", "lo", "mm", "un", "org", "ilo", "don", "nrv", "hrc",  # fragments
    "ilo.", "agenda", "congress", "supervisor", "therein", "escape",
    "the united nations", "joint committees", "ilo list",
    "red &", "the ( h )", "w. r. t. sea", "b. gate", "f. p. s.",
    "heli - pad", "i. e. helicopter", "be xiv", "awareness & vii",
    "acetylene cylinder", "pulley blocks", "switch board", "survey meter",
    "india ministry of petroleum", "hse training & awareness",
    "Victoria Contreras\nIssued",
    "Alexandra Taylor\nDepartment",
    "Anthony Knoll Apt",
    "Expiry Date",
    "Christian Vaughn\nIssue",
    "AP", "AZ",  # 2-letter state codes
    "Chemical",   # spaCy splits "Chemical Plant C"
])
def test_is_valid_person_entity_rejects_junk(junk):
    assert is_valid_person_entity(junk) is False


@pytest.mark.parametrize("name", [
    "Krista Roberts",
    "John Smith",
    "Priya Rao",
    "Jean-Luc Picard",
    "BHEL",
    "NVIDIA",
    "The United Nations",
    "Diane Miller\n",  # trailing-newline artifact collapses to a real name
])
def test_is_valid_person_entity_accepts_names(name):
    assert is_valid_person_entity(name) is True


class _FakeSpan:
    def __init__(self, text, label_):
        self.text = text
        self.label_ = label_


class _FakeDoc:
    def __init__(self, spans):
        self.ents = spans

    def __call__(self, text):
        return self  # mimics spaCy's nlp(text) call


def test_extract_all_applies_junk_filter():
    ex = object.__new__(EntityExtractor)
    ex.spacy_available = True
    ex.nlp = _FakeDoc([
        _FakeSpan("vii", "PERSON"),
        _FakeSpan("gb", "ORG"),
        _FakeSpan("Krista Roberts", "PERSON"),
    ])
    ents = ex.extract_all("some text")
    assert "Krista Roberts" in ents["personnel"]
    assert "vii" not in ents["personnel"]
    assert "gb" not in ents["personnel"]


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
