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

MEGHANA_HSR_LAYOUT = DemoRestaurant(
    id="meghana_hsr_layout",
    name="Meghana Biryani – HSR Layout",
    timezone="Asia/Kolkata",
    currency="INR",
    metadata=MappingProxyType(
        {
            "brand": "Meghana Biryani",
            "locality": "HSR Layout",
            "city": "Bengaluru",
            "scenario": "service_window_demo",
        }
    ),
)

DEMO_RESTAURANTS: Mapping[str, DemoRestaurant] = MappingProxyType({
    MEGHANA_INDIRANAGAR.id: MEGHANA_INDIRANAGAR,
    MEGHANA_HSR_LAYOUT.id: MEGHANA_HSR_LAYOUT,
})
