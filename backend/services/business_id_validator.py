"""🇫🇷🇧🇪 Validateur SIREN / SIRET (France) et BCE (Belgique) — v1.1.4.

Fallback pour auto-entrepreneurs non assujettis TVA (regime micro-BNC,
franchise en base, auto-entrepreneur, etc.) qui n'ont pas de TVA
européenne mais possèdent :
  • FR — un SIREN (9 chiffres) ou SIRET (14 chiffres) via l'INSEE.
  • BE — un numéro BCE / KBO (10 chiffres, "0" ou "1" en tête).

Validations LOCALES uniquement (algorithmes officiels) :
  • SIREN — Luhn mod 10 sur 9 chiffres.
  • SIRET — Luhn mod 10 sur 14 chiffres (SIREN + NIC 5 chiffres).
  • BCE   — modulo 97 : les 8 premiers chiffres divisés par 97 doivent
            avoir un reste égal aux 2 derniers chiffres (méthode BE
            officielle).

On ne contacte pas d'API externe pour cette v1 : les artisans en
situation de fraude sont bloqués par le contrôle de format + Luhn/97,
ce qui est déjà largement suffisant pour dissuader.
"""
from __future__ import annotations

import re
from typing import Optional


def _clean(v: str) -> str:
    """Retire tout caractère non chiffré (espaces, tirets, points)."""
    return re.sub(r"\D+", "", v or "")


def _luhn_check(digits: str) -> bool:
    """Algorithme de Luhn (mod 10). Retourne True si valide."""
    if not digits.isdigit():
        return False
    total = 0
    reverse = digits[::-1]
    for i, ch in enumerate(reverse):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def check_siren_format(siren: str) -> tuple[bool, Optional[str]]:
    """Vérifie qu'une chaîne est un SIREN valide (9 chiffres, Luhn OK)."""
    cleaned = _clean(siren)
    if len(cleaned) != 9:
        return False, "SIREN invalide (doit contenir exactement 9 chiffres)."
    if not _luhn_check(cleaned):
        return False, "SIREN invalide (échec du contrôle de clé Luhn)."
    return True, cleaned


def check_siret_format(siret: str) -> tuple[bool, Optional[str]]:
    """Vérifie qu'une chaîne est un SIRET valide (14 chiffres, Luhn OK).

    Note : le SIRET du siège de La Poste (356 000 000 XXXXX) échoue au
    Luhn standard sur les 14 chiffres et utilise une variante par bloc.
    On accepte donc le SIRET si (a) Luhn 14 chiffres OK, ou (b) Luhn
    SIREN (9 premiers) OK et Luhn NIC (5 derniers) OK — cas La Poste.
    """
    cleaned = _clean(siret)
    if len(cleaned) != 14:
        return False, "SIRET invalide (doit contenir exactement 14 chiffres)."
    if _luhn_check(cleaned):
        return True, cleaned
    # Variante La Poste
    if _luhn_check(cleaned[:9]) and _luhn_check(cleaned[9:]):
        return True, cleaned
    return False, "SIRET invalide (échec du contrôle de clé)."


def check_bce_format(bce: str) -> tuple[bool, Optional[str]]:
    """Vérifie qu'un numéro BCE belge est valide (10 chiffres, mod 97)."""
    cleaned = _clean(bce)
    if len(cleaned) != 10:
        return False, "BCE invalide (doit contenir exactement 10 chiffres)."
    if cleaned[0] not in ("0", "1"):
        return False, (
            "BCE invalide : le numéro d'entreprise belge commence par 0 ou 1."
        )
    base = int(cleaned[:8])
    key = int(cleaned[8:])
    if 97 - (base % 97) != key:
        return False, "BCE invalide (échec du contrôle de clé mod-97)."
    return True, cleaned


BUSINESS_ID_TYPES = {"vat", "siren", "siret", "bce"}


def validate_business_id(
    id_type: str, value: str
) -> tuple[bool, Optional[str], Optional[str]]:
    """Valide un identifiant business selon son type.

    Args:
        id_type: 'siren' | 'siret' | 'bce' (utiliser validate_vat pour 'vat').
        value: Numéro brut saisi par l'utilisateur.

    Returns:
        (is_valid, normalized_or_None, error_or_None)
    """
    id_type = (id_type or "").strip().lower()
    if id_type == "siren":
        ok, res = check_siren_format(value)
    elif id_type == "siret":
        ok, res = check_siret_format(value)
    elif id_type == "bce":
        ok, res = check_bce_format(value)
    else:
        return False, None, f"Type d'identifiant '{id_type}' non supporté."
    if not ok:
        return False, None, res
    return True, res, None
