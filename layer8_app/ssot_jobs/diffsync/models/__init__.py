"""DiffSync model class definitions for Layer8 SSoT integration."""

from layer8_app.ssot_jobs.diffsync.models.base.dcim import Building
from layer8_app.ssot_jobs.diffsync.models.nautobot.dcim import NautobotBuilding

__all__ = (
    "Building",
    "NautobotBuilding",
)
