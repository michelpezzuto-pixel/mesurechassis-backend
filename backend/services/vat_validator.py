"""Validateur de numéro de TVA européen — Build 11.3 (juin 2026).

Pour passer la Apple Review Guideline 3.1.1 + 3.1.3(c), MesureChâssis
se positionne désormais comme un service B2B professionnel : seuls les
utilisateurs avec un numéro de TVA européen valide peuvent s'inscrire
comme Admin ou Artisan (compte payant).

Stratégie de validation à 2 niveaux :
  1. CHECK FORMAT (toujours bloquant) : regex par pays. Refuse les
     numéros manifestement invalides.
  2. CHECK VIES (souple) : appel à l'API officielle européenne pour
     vérifier que la TVA EXISTE réellement. Si VIES est down/timeout,
     on accepte quand même (fallback) pour éviter de bloquer un
     utilisateur légitime à cause d'une panne de service externe.

API VIES :
  https://ec.europa.eu/taxation_customs/vies/checkVatService
  Gratuit, sans API key. Limité à ~10 req/s.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger("mesurechassis.vat")

VIES_API = "https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number"

# Regex par pays — couvre l'essentiel de l'UE pour le launch.
# Source : https://en.wikipedia.org/wiki/VAT_identification_number
COUNTRY_PATTERNS = {
    "AT": r"^ATU\d{8}$",                # Autriche
    "BE": r"^BE0?\d{9,10}$",             # Belgique (10 chiffres après BE0 ou BE)
    "BG": r"^BG\d{9,10}$",               # Bulgarie
    "CY": r"^CY\d{8}[A-Z]$",             # Chypre
    "CZ": r"^CZ\d{8,10}$",               # Tchéquie
    "DE": r"^DE\d{9}$",                  # Allemagne
    "DK": r"^DK\d{8}$",                  # Danemark
    "EE": r"^EE\d{9}$",                  # Estonie
    "EL": r"^EL\d{9}$",                  # Grèce (EL)
    "GR": r"^GR\d{9}$",                  # Grèce (GR alternative)
    "ES": r"^ES[A-Z0-9]\d{7}[A-Z0-9]$",   # Espagne
    "FI": r"^FI\d{8}$",                  # Finlande
    "FR": r"^FR[A-Z0-9]{2}\d{9}$",        # France
    "HR": r"^HR\d{11}$",                 # Croatie
    "HU": r"^HU\d{8}$",                  # Hongrie
    "IE": r"^IE\d{7}[A-Z]{1,2}$",         # Irlande
    "IT": r"^IT\d{11}$",                 # Italie
    "LT": r"^LT(\d{9}|\d{12})$",         # Lituanie
    "LU": r"^LU\d{8}$",                  # Luxembourg
    "LV": r"^LV\d{11}$",                 # Lettonie
    "MT": r"^MT\d{8}$",                  # Malte
    "NL": r"^NL\d{9}B\d{2}$",            # Pays-Bas
    "PL": r"^PL\d{10}$",                 # Pologne
    "PT": r"^PT\d{9}$",                  # Portugal
    "RO": r"^RO\d{2,10}$",               # Roumanie
    "SE": r"^SE\d{12}$",                 # Suède
    "SI": r"^SI\d{8}$",                  # Slovénie
    "SK": r"^SK\d{10}$",                 # Slovaquie
    # Ajouter UK / Suisse plus tard si besoin (hors UE).
}


def normalize_vat(vat: str) -> str:
    """Nettoie un numéro de TVA : majuscules + suppression espaces/tirets/points."""
    return re.sub(r"[\s\-.]+", "", (vat or "").upper())


def check_vat_format(vat: str) -> tuple[bool, Optional[str]]:
    """Vérifie le format d'un numéro de TVA européen.

    Retourne (is_valid, normalized_or_error_msg).
    """
    cleaned = normalize_vat(vat)
    if len(cleaned) < 4:
        return False, "Numéro de TVA trop court."
    country = cleaned[:2]
    if country not in COUNTRY_PATTERNS:
        return False, (
            f"Pays « {country} » non supporté pour le moment. "
            "Pays acceptés : BE, FR, DE, NL, LU, IT, ES, PT, AT, et "
            "tous les autres États membres de l'UE."
        )
    pattern = COUNTRY_PATTERNS[country]
    if not re.match(pattern, cleaned):
        return False, (
            f"Format de TVA {country} invalide. "
            f"Exemple attendu : {_example_for(country)}"
        )
    return True, cleaned


def _example_for(country: str) -> str:
    examples = {
        "BE": "BE0123456789",
        "FR": "FR12345678901",
        "DE": "DE123456789",
        "NL": "NL123456789B01",
        "LU": "LU12345678",
        "IT": "IT12345678901",
        "ES": "ESA12345678",
        "PT": "PT123456789",
        "AT": "ATU12345678",
        "PL": "PL1234567890",
    }
    return examples.get(country, f"{country}XXXXXXXXX")


async def check_vat_vies(vat_normalized: str, timeout: float = 5.0) -> tuple[bool, Optional[str]]:
    """Interroge l'API VIES officielle pour valider la TVA en vrai.

    Retourne (is_valid, optional_company_name).
    En cas de timeout / erreur réseau, on retourne (True, None) pour
    ne pas bloquer l'utilisateur — c'est un best-effort.
    """
    if len(vat_normalized) < 4:
        return False, None
    country = vat_normalized[:2]
    number = vat_normalized[2:]
    # Cas spécial Grèce : VIES utilise "EL" comme code, jamais "GR"
    if country == "GR":
        country = "EL"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                VIES_API,
                json={"countryCode": country, "vatNumber": number},
            )
            if resp.status_code != 200:
                logger.warning(
                    "VIES HTTP %s pour %s — fallback: on accepte",
                    resp.status_code,
                    vat_normalized,
                )
                return True, None  # fallback OK
            data = resp.json()
            # 🛡️ Fix Build 11.3.1 : VIES retourne parfois HTTP 200 avec
            # `valid: null` (Member State Service temporairement indisponible
            # — documenté par la Commission). On NE doit PAS rejeter dans
            # ce cas : on fallback en acceptant comme pour un timeout.
            if data.get("valid") is None:
                logger.warning(
                    "VIES valid=null pour %s (MS service temporairement KO) — fallback accept",
                    vat_normalized,
                )
                return True, None
            is_valid = bool(data.get("valid"))
            company_name = data.get("name") or None
            if not is_valid:
                logger.info("VIES KO pour %s", vat_normalized)
                return False, None
            return True, company_name
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.warning("VIES timeout/réseau pour %s : %s — fallback: on accepte", vat_normalized, e)
        return True, None  # fallback OK
    except Exception as e:  # noqa: BLE001
        logger.exception("VIES inattendu : %s", e)
        return True, None  # fallback OK


async def validate_vat(vat: str, *, skip_vies: bool = False) -> tuple[bool, Optional[str], Optional[str]]:
    """Validation complète : format + VIES.

    Args:
        vat: Numéro de TVA brut saisi par l'utilisateur.
        skip_vies: Si True, ne contacte pas VIES (ex: compte démo Apple).

    Returns:
        (is_valid, normalized_vat, company_name_or_error)
    """
    ok, normalized_or_err = check_vat_format(vat)
    if not ok:
        return False, None, normalized_or_err

    normalized = normalized_or_err  # type: ignore[assignment]
    assert normalized is not None

    if skip_vies:
        return True, normalized, None

    vies_ok, company_name = await check_vat_vies(normalized)
    if not vies_ok:
        return False, normalized, (
            "Ce numéro de TVA n'est pas reconnu par le registre européen "
            "VIES. Vérifiez la saisie ou contactez-nous si l'erreur persiste."
        )
    return True, normalized, company_name
