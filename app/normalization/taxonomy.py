"""
Taxonomy and Normalization Logic
"""
import re
from typing import Optional
from app.core.constants import CANONICAL_CATEGORIES, CATEGORY_ALIASES

# Keyword heuristics for normalizing raw document sections into canonical categories
SECTION_HEURISTICS = [
    (r"\b(early detection|catching it early)\b", "early_detection"),
    (r"\b(screens?|screening|mammograms?|colonoscop(y|ies)|pap smears?|psa tests?)\b", "screening"),
    (r"\b(symptoms?|warning signs?|feeling|physical signs?)\b", "symptoms"),
    (r"\b(signs?|clinical signs?|manifestations?)\b", "signs"),
    (r"\b(risk factors?|causes?|etiolog(y|ies)|who is at risk)\b", "risk_factors"),
    (r"\b(prevents?|prevention|reducing risks?|lifestyles?)\b", "prevention"),
    (r"\b(diagnos(is|tic|ed)|finding cancer|how is it diagnosed|detect(ion)?)\b", "diagnosis"),
    (r"\b(tests?|biops(y|ies)|scans?|mri|ct scans?|ultrasounds?|blood tests?|diagnostic tests?)\b", "diagnostic_tests"),
    (r"\b(stages?|staging|tnm|metastasis|spread)\b", "staging"),
    (r"\b(grades?|grading|differentiation)\b", "grading"),
    (r"\b(biomarkers?|her2|er/pr|egfr|braf|kras|msi|pdl1)\b", "biomarkers"),
    (r"\b(genetics?|genetic testing|brca|lynch syndrome|hereditary)\b", "genetics"),
    (r"\b(surger(y|ies)|surgical|mastectom(y|ies)|lumpectom(y|ies)|resections?|operations?)\b", "surgery"),
    (r"\b(chemotherap(y|ies)|chemo|cytotoxics?)\b", "chemotherapy"),
    (r"\b(radiat(ion|ing)|radiotherapy|beam)\b", "radiation_therapy"),
    (r"\b(immunotherap(y|ies)|checkpoints?|car-t|pembrolizumab)\b", "immunotherapy"),
    (r"\b(targeted therap(y|ies)|targeted drugs?|tyrosine kinase)\b", "targeted_therapy"),
    (r"\b(hormone therap(y|ies)|endocrine|tamoxifen|aromatase)\b", "hormone_therapy"),
    (r"\b(stem cells?|bone marrow|transplants?)\b", "stem_cell_transplant"),
    (r"\b(side effects?|toxicit(y|ies)|adverse events?)\b", "side_effects"),
    (r"\b(supportive care|support|palliative)\b", "supportive_care"),
    (r"\b(prognos(is|tic)|outlooks?|life expectancy)\b", "prognosis"),
    (r"\b(survivals?|survival rates?|5-year)\b", "survival"),
    (r"\b(recurrences?|relapses?|cancer coming back)\b", "recurrence"),
    (r"\b(follow-ups?|surveillance|monitoring)\b", "follow_up"),
    (r"\b(treat(ment|ments|ing)?|options?|therap(y|ies)|management)\b", "treatment"),
    (r"\b(types?|subtypes?|classifications?|histolog(y|ies))\b", "types_and_subtypes"),
    (r"\b(statistics?|incidence|mortalit(y|ies)|rates?|numbers?|how common)\b", "statistics"),
    (r"\b(clinical trials?|research stud(y|ies)|investigational)\b", "clinical_trials"),
    (r"\b(caregivers?|famil(y|ies)|supporting someone)\b", "caregiver_information"),
    (r"\b(living with|quality of life|coping|wellness)\b", "living_with_cancer"),
    (r"\b(childhood|pediatric|children)\b", "childhood_cancer"),
    (r"\b(terms?|glossar(y|ies)|definitions?|meaning)\b", "terminology"),
    (r"\b(overviews?|about|what is|introductions?|summary|summaries)\b", "overview"),
]


def resolve_public_category(value: str) -> str:
    """Resolve only explicit public names and aliases; never guess a category."""
    from app.core.errors import CategoryNotFoundError

    clean = value.strip().lower()
    slug = clean.replace(" ", "_").replace("-", "_")
    if slug in CANONICAL_CATEGORIES:
        return slug
    if clean in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[clean]
    raise CategoryNotFoundError(value)


def normalize_category(raw_title: str) -> str:
    """
    Normalizes a section heading or topic into one of the 37 canonical categories.
    """
    raw_lower = raw_title.strip().lower()

    # Direct canonical match
    slugified = raw_lower.replace(" ", "_").replace("-", "_")
    if slugified in CANONICAL_CATEGORIES:
        return slugified

    # Known alias match
    if raw_lower in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[raw_lower]

    # Regex heuristic search
    for pattern, canonical_cat in SECTION_HEURISTICS:
        if re.search(pattern, raw_lower):
            return canonical_cat

    return "overview"
