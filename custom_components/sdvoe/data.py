"""Custom types for RiverLink SDVoE Matrix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import RiverLinkApiClient
    from .coordinator import RiverLinkDataUpdateCoordinator


type RiverLinkConfigEntry = ConfigEntry[RiverLinkData]


@dataclass
class RiverLinkData:
    """Data for the RiverLink integration."""

    client: RiverLinkApiClient
    coordinator: RiverLinkDataUpdateCoordinator
    integration: Integration
