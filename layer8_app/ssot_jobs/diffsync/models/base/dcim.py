"""Base DCIM subclasses DiffSyncModel for nautobot_ssot_layer8 data sync."""

from typing import List, Optional, Annotated
from uuid import UUID

from diffsync import DiffSyncModel

from nautobot_ssot.contrib import CustomFieldAnnotation


class Building(DiffSyncModel):
    """Base Building model."""

    _modelname = "building"
    _identifiers = ("name",)
    _attributes = ("status__name", "external_id")

    name: str
    status__name: str
    uuid: Optional[UUID]
    external_id: Annotated[int, CustomFieldAnnotation(key="external_id")]


Building.update_forward_refs()
