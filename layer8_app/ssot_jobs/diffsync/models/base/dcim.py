"""Base DCIM subclasses DiffSyncModel for nautobot_ssot_layer8 data sync."""

from typing import List, Optional, Annotated
from uuid import UUID

from diffsync import DiffSyncModel

from nautobot_ssot.contrib import CustomFieldAnnotation


class Building(DiffSyncModel):
    """Base Building model."""

    _modelname = "building"
    _identifiers = ("name",)
    _attributes = ("status__name", "external_id", "longitude", "latitude", "technical_reference")
    _children = {"room": "rooms"}

    name: str
    status__name: str
    uuid: Optional[UUID]
    rooms: List["Room"] = list()
    external_id: int
    longitude: Optional[float]
    latitude: Optional[float]
    technical_reference: Optional[str]


class Room(DiffSyncModel):
    """Base Room model."""

    _modelname = "room"
    _identifiers = ("name", "parent__name", "external_id")
    _attributes = ("status__name",)

    name: str
    parent__name: Optional[str]  # Building name
    status__name: str
    uuid: Optional[UUID]
    external_id: int


Building.update_forward_refs()
Room.update_forward_refs()
