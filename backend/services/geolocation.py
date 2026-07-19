"""🗺️ Service de géolocalisation IP → ville.

Cascade de 2 fournisseurs HTTPS gratuits pour maximiser la robustesse :
  1. **freeipapi.com** (primary) — HTTPS, illimité, sans clé, très riche
  2. **ipwho.is** (fallback) — HTTPS, 10 000 req/mois, sans clé

Aucune donnée personnelle stockée hormis la ville + coordonnées
approximatives (RGPD friendly).

⚠️ Historique : le service précédent (`ip-api.com`) fonctionne uniquement
en HTTP non chiffré sur le tier gratuit, et Railway bloque les appels
sortants non chiffrés en prod → toutes les géolocs échouaient silencieusement.

Usage :
    from services.geolocation import geolocate_from_request
    geo = await geolocate_from_request(request)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from fastapi import Request

logger = logging.getLogger("geolocation")

# Timeout court : si l'API ne répond pas en 3s, on renonce (l'inscription
# doit rester rapide, la géoloc est un bonus non bloquant).
_TIMEOUT = httpx.Timeout(3.0, connect=2.0)


def _extract_client_ip(request: Request) -> str:
    """Extrait l'IP publique du client (gère X-Forwarded-For sur Railway/K8s)."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        # Le premier IP dans la chaîne = client réel
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real.strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


async def _try_freeipapi(client: httpx.AsyncClient, ip: str) -> Optional[dict[str, Any]]:
    """Primary : freeipapi.com — HTTPS, illimité, sans clé."""
    try:
        r = await client.get(
            f"https://freeipapi.com/api/json/{ip}",
            follow_redirects=True,
        )
        if r.status_code != 200:
            logger.warning(
                "freeipapi HTTP %s for IP %s: %s",
                r.status_code, ip, r.text[:200],
            )
            return None
        data = r.json()
        lat = data.get("latitude")
        lng = data.get("longitude")
        if not lat or not lng:
            return None
        return {
            "city": data.get("cityName") or "",
            "region": data.get("regionName") or "",
            "country": data.get("countryName") or "",
            "country_code": data.get("countryCode") or "",
            "lat": float(lat),
            "lng": float(lng),
            "_source": "freeipapi",
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("freeipapi FAILED for IP %s: %s", ip, e)
        return None


async def _try_ipwhois(client: httpx.AsyncClient, ip: str) -> Optional[dict[str, Any]]:
    """Fallback : ipwho.is — HTTPS, 10 000 req/mois, sans clé."""
    try:
        r = await client.get(f"https://ipwho.is/{ip}", follow_redirects=True)
        if r.status_code != 200:
            logger.warning(
                "ipwhois HTTP %s for IP %s: %s",
                r.status_code, ip, r.text[:200],
            )
            return None
        data = r.json()
        if not data.get("success"):
            logger.warning(
                "ipwhois not successful for IP %s: %s",
                ip, data.get("message", "no message"),
            )
            return None
        lat = data.get("latitude")
        lng = data.get("longitude")
        return {
            "city": data.get("city") or "",
            "region": data.get("region") or "",
            "country": data.get("country") or "",
            "country_code": data.get("country_code") or "",
            "lat": float(lat) if lat is not None else None,
            "lng": float(lng) if lng is not None else None,
            "_source": "ipwhois",
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("ipwhois FAILED for IP %s: %s", ip, e)
        return None


async def geolocate_ip(ip: str) -> Optional[dict[str, Any]]:
    """Résout une IP en dict {city, region, country, lat, lng}.

    Cascade : freeipapi → ipwhois. Retourne None seulement si les deux
    échouent. Non bloquant : l'appelant doit gérer le None (fallback =
    pas de géoloc pour cet utilisateur).
    """
    if not ip or ip in ("unknown", "127.0.0.1", "localhost") or ip.startswith(
        ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
         "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
         "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")
    ):
        logger.info("Geolocation skipped (IP privée/locale) : %s", ip)
        return None

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # 1) Primary
        geo = await _try_freeipapi(client, ip)
        if geo and geo.get("lat") and geo.get("lng"):
            logger.info(
                "Geoloc OK via freeipapi : %s → %s, %s",
                ip, geo.get("city"), geo.get("country"),
            )
            return geo
        # 2) Fallback
        geo = await _try_ipwhois(client, ip)
        if geo and geo.get("lat") and geo.get("lng"):
            logger.info(
                "Geoloc OK via ipwhois : %s → %s, %s",
                ip, geo.get("city"), geo.get("country"),
            )
            return geo

    logger.warning("Geoloc TOTAL FAIL for IP %s (both providers down)", ip)
    return None


async def geolocate_from_request(request: Request) -> Optional[dict[str, Any]]:
    """Combine l'extraction IP + résolution en un seul appel."""
    ip = _extract_client_ip(request)
    if not ip:
        logger.warning("Geolocation : impossible d'extraire l'IP du client")
        return None
    return await geolocate_ip(ip)
