"""Dictionnaires de traduction pour les exports backend (PDF principalement).

Ce module centralise la traduction des labels affichés dans le PDF, le CSV
et l'Excel pour rester cohérent avec l'i18n frontend (FR, NL, EN).

Usage :
    from i18n_labels import pdf_labels
    L = pdf_labels(lang)            # `lang` ∈ {"fr", "nl", "en"} – fallback FR
    L["client"]                      # "Client" / "Klant" / "Client"
    L["field"]["bay_height"]         # libellé champ traduit
"""
from __future__ import annotations

from typing import Any

# 🌍 Dictionnaire principal des labels traduits par langue.
# Toute clé manquante dans NL/EN retombe sur la version FR (helper `pdf_labels`).
_PDF_LABELS: dict[str, dict[str, Any]] = {
    "fr": {
        "internal_banner": (
            "<b>DOCUMENT INTERNE</b> — Fiche technique de mesurage, usage strictement interne"
        ),
        "fiche": "Fiche Chantier",
        "client": "Client",
        "address": "Adresse",
        "status": "Statut",
        "date": "Date",
        "openings_section": "Ouvertures",
        "measure_col": "Mesure",
        "value_col": "Valeur (mm)",
        "slope_angle": "Angle de pente",
        "photos_section": "📷 Photos chantier — Anti-litige",
        "photos_caption": (
            "Preuves photographiques de l'état existant au moment de la prise de mesures."
        ),
        "photo_unreadable": "Photo {idx} illisible",
        "photo_default_caption": "Photo {idx}",
        "via": "via MesureChâssis",
        "field": {
            "bay_height": "Hauteur baie",
            "bay_width": "Largeur baie",
            "bay_diagonal_1": "Diagonale 1",
            "bay_diagonal_2": "Diagonale 2",
            "floor_reserve": "Réserve Sol Fini",
            "bloc_thickness": "Épaisseur Bloc Béton",
            "insulation_thickness": "Épaisseur Isolant",
            "finish_outer": "Finition extérieure",
            "finish_inner": "Finition intérieure",
            "wall_type": "Type paroi",
            "breastwork_present": "Allège — présence",
            "breastwork_height": "Allège — hauteur",
            "feuillure_left": "Feuillure gauche",
            "feuillure_right": "Feuillure droite",
            "feuillure_top": "Feuillure haute",
            "sill_installed": "Seuil — déjà posé",
            "sill_thickness": "Seuil — épaisseur future",
            "horizontal_cut": "Coupe horizontale",
            "mark_1m_active": "Trait 1m — actif",
            "mark_1m_brut": "Trait 1m — mesure brute",
            "triangle_base": "Triangle — base",
            "triangle_height": "Triangle — hauteur",
            "oeil_diameter": "Œil-de-bœuf — diamètre",
            "garage_lintel": "Porte garage — linteau",
            "garage_ecoincon_left": "Porte garage — écoinçon gauche",
            "garage_ecoincon_right": "Porte garage — écoinçon droit",
            "width_top": "Largeur haut",
            "width_middle": "Largeur milieu",
            "width_bottom": "Largeur bas",
            "height_left": "Hauteur gauche",
            "height_middle": "Hauteur milieu",
            "height_right": "Hauteur droite",
            "diag_1": "Diagonale 1",
            "diag_2": "Diagonale 2",
            "height_quarter_left": "Hauteur 1/4 gauche",
            "height_quarter_right": "Hauteur 1/4 droite",
            "height_small": "Hauteur petite",
            "height_large": "Hauteur grande",
            "width_small": "Largeur petite",
            "width_intermediate": "Largeur intermédiaire",
        },
        "yes": "OUI",
        "no": "NON",
    },
    "nl": {
        "internal_banner": (
            "<b>INTERN DOCUMENT</b> — Technische metingsfiche, strikt intern gebruik"
        ),
        "fiche": "Projectfiche",
        "client": "Klant",
        "address": "Adres",
        "status": "Status",
        "date": "Datum",
        "openings_section": "Openingen",
        "measure_col": "Meting",
        "value_col": "Waarde (mm)",
        "slope_angle": "Hellingshoek",
        "photos_section": "📷 Foto's project — Anti-geschil",
        "photos_caption": (
            "Fotografische bewijzen van de bestaande staat op het moment van meting."
        ),
        "photo_unreadable": "Foto {idx} onleesbaar",
        "photo_default_caption": "Foto {idx}",
        "via": "via MesureChâssis",
        "field": {
            "bay_height": "Hoogte baai",
            "bay_width": "Breedte baai",
            "bay_diagonal_1": "Diagonaal 1",
            "bay_diagonal_2": "Diagonaal 2",
            "floor_reserve": "Vloerreserve",
            "bloc_thickness": "Dikte betonblok",
            "insulation_thickness": "Dikte isolatie",
            "finish_outer": "Afwerking buiten",
            "finish_inner": "Afwerking binnen",
            "wall_type": "Muurtype",
            "breastwork_present": "Borstwering — aanwezig",
            "breastwork_height": "Borstwering — hoogte",
            "feuillure_left": "Sponning links",
            "feuillure_right": "Sponning rechts",
            "feuillure_top": "Sponning boven",
            "sill_installed": "Dorpel — al geplaatst",
            "sill_thickness": "Dorpel — toekomstige dikte",
            "horizontal_cut": "Horizontale snede",
            "mark_1m_active": "1m peilmaat — actief",
            "mark_1m_brut": "1m peilmaat — ruwe maat",
            "triangle_base": "Driehoek — basis",
            "triangle_height": "Driehoek — hoogte",
            "oeil_diameter": "Rondraam — diameter",
            "garage_lintel": "Garagedeur — latei",
            "garage_ecoincon_left": "Garagedeur — hoekstuk links",
            "garage_ecoincon_right": "Garagedeur — hoekstuk rechts",
            "width_top": "Breedte boven",
            "width_middle": "Breedte midden",
            "width_bottom": "Breedte onder",
            "height_left": "Hoogte links",
            "height_middle": "Hoogte midden",
            "height_right": "Hoogte rechts",
            "diag_1": "Diagonaal 1",
            "diag_2": "Diagonaal 2",
            "height_quarter_left": "Hoogte 1/4 links",
            "height_quarter_right": "Hoogte 1/4 rechts",
            "height_small": "Hoogte klein",
            "height_large": "Hoogte groot",
            "width_small": "Breedte klein",
            "width_intermediate": "Breedte intermediair",
        },
        "yes": "JA",
        "no": "NEE",
    },
    "en": {
        "internal_banner": (
            "<b>INTERNAL DOCUMENT</b> — Technical measurement sheet, strictly internal use"
        ),
        "fiche": "Project Sheet",
        "client": "Client",
        "address": "Address",
        "status": "Status",
        "date": "Date",
        "openings_section": "Openings",
        "measure_col": "Measurement",
        "value_col": "Value (mm)",
        "slope_angle": "Slope angle",
        "photos_section": "📷 Site photos — Anti-dispute",
        "photos_caption": (
            "Photographic evidence of the existing state at the time of measurement."
        ),
        "photo_unreadable": "Photo {idx} unreadable",
        "photo_default_caption": "Photo {idx}",
        "via": "via MesureChâssis",
        "field": {
            "bay_height": "Bay height",
            "bay_width": "Bay width",
            "bay_diagonal_1": "Diagonal 1",
            "bay_diagonal_2": "Diagonal 2",
            "floor_reserve": "Floor reserve",
            "bloc_thickness": "Concrete block thickness",
            "insulation_thickness": "Insulation thickness",
            "finish_outer": "Outer finish",
            "finish_inner": "Inner finish",
            "wall_type": "Wall type",
            "breastwork_present": "Breastwork — present",
            "breastwork_height": "Breastwork — height",
            "feuillure_left": "Left rebate",
            "feuillure_right": "Right rebate",
            "feuillure_top": "Top rebate",
            "sill_installed": "Sill — already installed",
            "sill_thickness": "Sill — future thickness",
            "horizontal_cut": "Horizontal cut",
            "mark_1m_active": "1m mark — active",
            "mark_1m_brut": "1m mark — raw measure",
            "triangle_base": "Triangle — base",
            "triangle_height": "Triangle — height",
            "oeil_diameter": "Oculus — diameter",
            "garage_lintel": "Garage door — lintel",
            "garage_ecoincon_left": "Garage door — left jamb",
            "garage_ecoincon_right": "Garage door — right jamb",
            "width_top": "Top width",
            "width_middle": "Middle width",
            "width_bottom": "Bottom width",
            "height_left": "Left height",
            "height_middle": "Middle height",
            "height_right": "Right height",
            "diag_1": "Diagonal 1",
            "diag_2": "Diagonal 2",
            "height_quarter_left": "Quarter left height",
            "height_quarter_right": "Quarter right height",
            "height_small": "Small height",
            "height_large": "Large height",
            "width_small": "Small width",
            "width_intermediate": "Intermediate width",
        },
        "yes": "YES",
        "no": "NO",
    },
}

# Statuts traduits (priorité au dictionnaire frontend pour la cohérence visuelle).
_STATUS_LABELS: dict[str, dict[str, str]] = {
    "fr": {
        "devis_a_faire": "Devis à faire",
        "a_mesurer": "À mesurer",
        "technique_a_valider": "Technique à valider",
        "en_commande": "En commande",
        "en_fabrication": "En fabrication",
        "cloture": "Clôturé",
    },
    "nl": {
        "devis_a_faire": "Offerte op te maken",
        "a_mesurer": "Te meten",
        "technique_a_valider": "Technisch te valideren",
        "en_commande": "Besteld",
        "en_fabrication": "In productie",
        "cloture": "Afgesloten",
    },
    "en": {
        "devis_a_faire": "Quote to make",
        "a_mesurer": "To measure",
        "technique_a_valider": "Technical validation",
        "en_commande": "Ordered",
        "en_fabrication": "In production",
        "cloture": "Closed",
    },
}


def _normalize_lang(lang: str | None) -> str:
    """Normalise une langue arbitraire vers une langue supportée (FR par défaut)."""
    if not lang:
        return "fr"
    code = lang.lower().split("-")[0].split("_")[0]
    if code in _PDF_LABELS:
        return code
    return "fr"


def pdf_labels(lang: str | None) -> dict[str, Any]:
    """Retourne le dictionnaire de labels traduits pour la langue demandée.

    Fallback : si une clé n'existe pas dans la langue demandée, on utilise
    le dictionnaire FR (référence).
    """
    code = _normalize_lang(lang)
    base = _PDF_LABELS["fr"]
    target = _PDF_LABELS[code]
    # Fusion peu profonde + fusion profonde du sous-dict `field`.
    merged: dict[str, Any] = {**base, **target}
    merged["field"] = {**base["field"], **target.get("field", {})}
    return merged


def status_label_i18n(status: str, lang: str | None = None) -> str:
    """Retourne le libellé statut traduit (fallback : code brut)."""
    code = _normalize_lang(lang)
    return _STATUS_LABELS[code].get(status, _STATUS_LABELS["fr"].get(status, status))


# 🗂️ En-têtes CSV / XLSX traduits (clés communes aux deux formats).
_CSV_HEADERS: dict[str, list[str]] = {
    "fr": [
        "Chantier", "Adresse", "Code Postal", "Ville", "Statut",
        "Label", "Type", "Forme", "Rénovation",
        "Largeur baie (mm)", "Hauteur baie (mm)",
        "Diag 1 (mm)", "Diag 2 (mm)", "Diag1 OK", "Diag2 OK",
        "L. haut (mm)", "L. bas (mm)",
        "H. gauche (mm)", "H. droite (mm)",
        "L. milieu (mm)", "H. milieu (mm)",
        "L. petite (mm)", "L. inter (mm)",
        "H. petite (mm)", "H. grande (mm)",
        "Réserve sol (mm)", "Épaisseur bloc (mm)",
        "Paroi", "Épais. isolant (mm)",
        "Finition ext (mm)", "Finition int (mm)",
        "Angle pente (°)", "Alertes", "Date mesure",
    ],
    "en": [
        "Project", "Address", "Postal code", "City", "Status",
        "Label", "Type", "Shape", "Renovation",
        "Bay width (mm)", "Bay height (mm)",
        "Diag 1 (mm)", "Diag 2 (mm)", "Diag1 OK", "Diag2 OK",
        "W. top (mm)", "W. bottom (mm)",
        "H. left (mm)", "H. right (mm)",
        "W. middle (mm)", "H. middle (mm)",
        "W. small (mm)", "W. inter (mm)",
        "H. small (mm)", "H. large (mm)",
        "Floor reserve (mm)", "Block thickness (mm)",
        "Wall", "Insulation thickness (mm)",
        "Outer finish (mm)", "Inner finish (mm)",
        "Slope angle (°)", "Alerts", "Measure date",
    ],
    "nl": [
        "Project", "Adres", "Postcode", "Plaats", "Status",
        "Label", "Type", "Vorm", "Renovatie",
        "Breedte baai (mm)", "Hoogte baai (mm)",
        "Diag 1 (mm)", "Diag 2 (mm)", "Diag1 OK", "Diag2 OK",
        "B. boven (mm)", "B. onder (mm)",
        "H. links (mm)", "H. rechts (mm)",
        "B. midden (mm)", "H. midden (mm)",
        "B. klein (mm)", "B. inter (mm)",
        "H. klein (mm)", "H. groot (mm)",
        "Vloerreserve (mm)", "Blok-dikte (mm)",
        "Muurtype", "Isolatie-dikte (mm)",
        "Afwerking buiten (mm)", "Afwerking binnen (mm)",
        "Hellingshoek (°)", "Waarschuwingen", "Meetdatum",
    ],
}

_CSV_YES_NO: dict[str, tuple[str, str]] = {
    "fr": ("oui", "non"),
    "en": ("yes", "no"),
    "nl": ("ja", "nee"),
}

# Mots pour formes / blocs (utilisés dans la colonne CSV "Forme" + "Type").
_CSV_WORDS: dict[str, dict[str, str]] = {
    "fr": {
        "trapezoidal": "trapézoïdal",
        "rectangular": "rectangulaire",
        "photos_block": "[PHOTOS ANTI-LITIGE]",
        "photo_default": "Photo {idx}",
        "col_index": "#",
        "col_caption": "Légende",
        "col_format": "Format",
    },
    "en": {
        "trapezoidal": "trapezoidal",
        "rectangular": "rectangular",
        "photos_block": "[ANTI-DISPUTE PHOTOS]",
        "photo_default": "Photo {idx}",
        "col_index": "#",
        "col_caption": "Caption",
        "col_format": "Format",
    },
    "nl": {
        "trapezoidal": "trapeziumvormig",
        "rectangular": "rechthoekig",
        "photos_block": "[FOTO'S ANTI-GESCHIL]",
        "photo_default": "Foto {idx}",
        "col_index": "#",
        "col_caption": "Bijschrift",
        "col_format": "Formaat",
    },
}


def csv_headers(lang: str | None) -> list[str]:
    return _CSV_HEADERS[_normalize_lang(lang)]


def csv_yes(lang: str | None) -> str:
    return _CSV_YES_NO[_normalize_lang(lang)][0]


def csv_no(lang: str | None) -> str:
    return _CSV_YES_NO[_normalize_lang(lang)][1]


def csv_word(key: str, lang: str | None) -> str:
    code = _normalize_lang(lang)
    return _CSV_WORDS[code].get(key, _CSV_WORDS["fr"].get(key, key))


# 📊 Libellés spécifiques XLSX (titres feuilles, en-têtes, "Client", etc.)
_XLSX_LABELS: dict[str, dict[str, Any]] = {
    "fr": {
        "title": "MesureChâssis — Fiche Chantier",
        "sheet_chantier": "Chantier",
        "sheet_mesures": "Mesures",
        "sheet_photos": "Photos site",
        "pair": {
            "client": "Client",
            "address": "Adresse",
            "postal": "Code postal",
            "city": "Ville",
            "status": "Statut",
            "created_at": "Date création",
            "appointment": "Rendez-vous",
            "notes": "Notes",
            "nb_openings": "Nb. ouvertures",
            "nb_photos": "Nb. photos site",
        },
        "cols": [
            "Libellé", "Type bloc", "Forme", "Rénovation",
            "L baie (mm)", "H baie (mm)", "Diag 1 (mm)", "Diag 2 (mm)",
            "Diag1 OK", "Diag2 OK",
            "L. haut (mm)", "L. bas (mm)", "H. gauche (mm)", "H. droite (mm)",
            "L. milieu (mm)", "H. milieu (mm)",
            "H. 1/4 G (mm)", "H. 1/4 D (mm)",
            "L. petite (mm)", "L. inter (mm)",
            "H. petite (mm)", "H. grande (mm)",
            "Réserve sol (mm)", "Épais. bloc béton (mm)",
            "Type paroi", "Épais. isolant (mm)",
            "Finition ext (mm)", "Finition int (mm)",
            "Angle pente (°)", "Alertes", "Date mesure",
        ],
        "photo_cols": ["#", "Légende", "Format", "Taille (caractères)"],
    },
    "en": {
        "title": "MesureChâssis — Project Sheet",
        "sheet_chantier": "Project",
        "sheet_mesures": "Measurements",
        "sheet_photos": "Site photos",
        "pair": {
            "client": "Client",
            "address": "Address",
            "postal": "Postal code",
            "city": "City",
            "status": "Status",
            "created_at": "Created on",
            "appointment": "Appointment",
            "notes": "Notes",
            "nb_openings": "Nb. openings",
            "nb_photos": "Nb. site photos",
        },
        "cols": [
            "Label", "Block type", "Shape", "Renovation",
            "Bay width (mm)", "Bay height (mm)", "Diag 1 (mm)", "Diag 2 (mm)",
            "Diag1 OK", "Diag2 OK",
            "W. top (mm)", "W. bottom (mm)", "H. left (mm)", "H. right (mm)",
            "W. middle (mm)", "H. middle (mm)",
            "H. 1/4 L (mm)", "H. 1/4 R (mm)",
            "W. small (mm)", "W. inter (mm)",
            "H. small (mm)", "H. large (mm)",
            "Floor reserve (mm)", "Concrete block thickness (mm)",
            "Wall type", "Insulation thickness (mm)",
            "Outer finish (mm)", "Inner finish (mm)",
            "Slope angle (°)", "Alerts", "Measure date",
        ],
        "photo_cols": ["#", "Caption", "Format", "Size (chars)"],
    },
    "nl": {
        "title": "MesureChâssis — Projectfiche",
        "sheet_chantier": "Project",
        "sheet_mesures": "Metingen",
        "sheet_photos": "Foto's site",
        "pair": {
            "client": "Klant",
            "address": "Adres",
            "postal": "Postcode",
            "city": "Plaats",
            "status": "Status",
            "created_at": "Aanmaakdatum",
            "appointment": "Afspraak",
            "notes": "Notities",
            "nb_openings": "Aantal openingen",
            "nb_photos": "Aantal foto's",
        },
        "cols": [
            "Label", "Bloktype", "Vorm", "Renovatie",
            "B baai (mm)", "H baai (mm)", "Diag 1 (mm)", "Diag 2 (mm)",
            "Diag1 OK", "Diag2 OK",
            "B. boven (mm)", "B. onder (mm)", "H. links (mm)", "H. rechts (mm)",
            "B. midden (mm)", "H. midden (mm)",
            "H. 1/4 L (mm)", "H. 1/4 R (mm)",
            "B. klein (mm)", "B. inter (mm)",
            "H. klein (mm)", "H. groot (mm)",
            "Vloerreserve (mm)", "Dikte betonblok (mm)",
            "Muurtype", "Isolatie-dikte (mm)",
            "Afwerking buiten (mm)", "Afwerking binnen (mm)",
            "Hellingshoek (°)", "Waarschuwingen", "Meetdatum",
        ],
        "photo_cols": ["#", "Bijschrift", "Formaat", "Grootte (tekens)"],
    },
}


def xlsx_labels(lang: str | None) -> dict[str, Any]:
    code = _normalize_lang(lang)
    base = _XLSX_LABELS["fr"]
    target = _XLSX_LABELS[code]
    merged: dict[str, Any] = {**base, **target}
    merged["pair"] = {**base["pair"], **target.get("pair", {})}
    return merged
