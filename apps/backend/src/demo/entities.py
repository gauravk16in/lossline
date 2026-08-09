"""Authoritative restaurant profiles for demo-only synthetic data."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class DemoRestaurant:
    id: str
    name: str
    timezone: str
    currency: str
    metadata: Mapping[str, str]


MEGHANA_INDIRANAGAR = DemoRestaurant(
    id="meghana_indiranagar",
    name="Meghana Biryani – Indiranagar",
    timezone="Asia/Kolkata",
    currency="INR",
    metadata=MappingProxyType(
        {
            "brand": "Meghana Biryani",
            "locality": "Indiranagar",
            "city": "Bengaluru",
            "scenario": "lunch_rush",
        }
    ),
)

DEMO_RESTAURANTS: Mapping[str, DemoRestaurant] = MappingProxyType(
    {MEGHANA_INDIRANAGAR.id: MEGHANA_INDIRANAGAR}
)
