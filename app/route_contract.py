"""Contract helpers for the Spring route calculation API."""

from __future__ import annotations


TRANSPORT_TO_API_TYPE = {
    "walk": "WALK",
    "public": "PUBLIC_TRANSIT",
    "bicycle": "BICYCLE",
    "car": "CAR",
}


def build_route_request(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    transport: str,
) -> dict:
    return {
        "origin": {"latitude": start_lat, "longitude": start_lon},
        "destination": {"latitude": end_lat, "longitude": end_lon},
        "transportType": TRANSPORT_TO_API_TYPE[transport],
    }
