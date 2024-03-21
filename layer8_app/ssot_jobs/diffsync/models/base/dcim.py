"""Base DCIM subclasses DiffSyncModel for nautobot_ssot_layer8 data sync."""

from typing import List, Optional
from uuid import UUID

from diffsync import DiffSyncModel


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


class Namespace(DiffSyncModel):
    """Base Namespace model."""

    _modelname = "namespace"
    _identifiers = ("name",)
    _attributes = ()
    _children = {}

    name: str
    description: Optional[str]
    uuid: Optional[UUID]


class Prefix(DiffSyncModel):
    """Base Prefix model."""

    _modelname = "prefix"
    _identifiers = ("prefix", "namespace")
    _attributes = ()
    _children = {}

    prefix: str
    namespace: str
    uuid: Optional[UUID]


class IPAddress(DiffSyncModel):
    """Base IPAddress model."""

    _modelname = "ipaddr"
    _identifiers = (
        "address",
        "prefix",
        "namespace",
    )
    _attributes = ()
    _children = {}

    address: str
    prefix: str
    namespace: str
    uuid: Optional[UUID]


class VLANGroup(DiffSyncModel):
    """Base VLANGroup model."""

    _modelname = "vlangroup"
    _identifiers = ("name",)
    _attributes = ()
    _children = {"vlan": "vlans"}

    name: str
    vlans: List["VLAN"] = list()
    uuid: Optional[UUID]


class VLAN(DiffSyncModel):
    """Base VLAN model."""

    _modelname = "vlan"
    _identifiers = ("vid", "name", "vlangroup")
    _attributes = ()
    _children = {}

    vid: int
    name: str
    vlangroup: Optional[str]
    uuid: Optional[UUID]


Building.update_forward_refs()
Room.update_forward_refs()
Namespace.update_forward_refs()
Prefix.update_forward_refs()
IPAddress.update_forward_refs()
VLANGroup.update_forward_refs()
VLAN.update_forward_refs()
