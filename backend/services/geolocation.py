"""🗺️ Service de géolocalisation IP → ville.

Utilise l'API publique **ip-api.com** (gratuite, 45 req/min, aucune clé
requise). Précision : ville. Aucune donnée personnelle stockée hormis
la ville + coordonnées approximatives (RGPD friendly).

Usage :
    from services.geolocation import geolocate_from_request
    geo = await geolocate_from_request(request)
    # geo = {"city": "Bruxelles", "region": "Brussels Capital",
    #        "country": "BE", "lat": 50.85, "lng": 4.35}
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from fastapi import Request

logger = logging.getLogger("geolocation")

# Timeout court : si ip-api ne répond pas en 3s, on renonce (l'inscription
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


async def geolocate_ip(ip: str) -> Optional[dict[str, Any]]:
    """Résout une IP en dict {city, region, country, lat, lng}.

    Retourne None en cas d'erreur / IP privée / timeout. Non bloquant :
    l'appelant doit gérer le None (fallback = pas de géoloc pour cet utilisateur).
    """
    if not ip or ip in ("unknown", "127.0.0.1", "localhost") or ip.startswith(
        ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
         "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
         "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")
    ):
        return None

    url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city,lat,lon"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
            if data.get("status") != "success":
                return None
            return {
                "city": data.get("city") or "",
                "region": data.get("regionName") or "",
                "country": data.get("country") or "",
                "country_code": data.get("countryCode") or "",
                "lat": float(data.get("lat", 0)) or None,
                "lng": float(data.get("lon", 0)) or None,
            }
    except Exception as e:  # noqa: BLE001
        logger.info("Geolocation failed for IP %s: %s", ip, e)
        return None


async def geolocate_from_request(request: Request) -> Optional[dict[str, Any]]:
    """Combine l'extraction IP + résolution en un seul appel."""
    ip = _extract_client_ip(request)
    if not ip:
        return None
    return await geolocate_ip(ip)
