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
    _attributes = ("description",)
    _children = {"prefix": "prefixes"}

    name: str
    description: Optional[str]
    uuid: Optional[UUID]
    prefixes: List["Prefix"] = list()


class Prefix(DiffSyncModel):
    """Base Prefix model."""

    _modelname = "prefix"
    _identifiers = ("prefix", "namespace")
    _attributes = (
        "description",
        "type",
    )
    _children = {}

    prefix: str
    namespace: str
    type: str
    status: Optional[str]
    description: str
    uuid: Optional[UUID]


class VLANGroup(DiffSyncModel):
    """Base VLANGroup model."""

    _modelname = "vlangroup"
    _identifiers = ("name",)
    _attributes = ("location__name",)
    _children = {"vlan": "vlans"}

    name: str
    vlans: List["VLAN"] = list()
    location__name: str
    uuid: Optional[UUID]


class VLAN(DiffSyncModel):
    """Base VLAN model."""

    _modelname = "vlan"
    _identifiers = ("vid", "name", "vlangroup")
    _attributes = ("location__name",)
    _children = {}

    vid: int
    name: str
    vlangroup: Optional[str]
    location__name: Optional[str]
    uuid: Optional[UUID]


class Device(DiffSyncModel):
    """Base Device model."""

    _modelname = "device"
    _identifiers = (
        "name",
        "location__name",
    )
    _attributes = ("monitoring_profile", "device_type", "manufacturer", "serial", "role")
    _children = {"interface": "interfaces"}

    name: str
    device_type: str
    manufacturer: str
    serial: Optional[str]
    platform: Optional[str]
    monitoring_profile: Optional[dict]
    location__name: str
    role: str
    interfaces: List["Interface"] = list()

    uuid: Optional[UUID]


class Interface(DiffSyncModel):
    """Base Interface model."""

    _modelname = "interface"
    _identifiers = (
        "name",
        "device__name",
        "device__location__name",
    )
    _attributes = ("type", "description", "status", "mgmt_only", "monitoring_profile")
    _children = {"ipaddr": "ipaddrs"}

    name: str
    device__name: str
    device__location__name: str
    type: str
    status: str
    description: Optional[str] = None
    monitoring_profile: Optional[dict]
    mac_address: Optional[str]
    ipaddrs: List["IPAddress"] = list()
    mgmt_only: Optional[bool] = False
    # enabled: bool

    uuid: Optional[UUID]


class IPAddress(DiffSyncModel):
    """Base IPAddress model."""

    _modelname = "ipaddr"
    _identifiers = (
        "address",
        "namespace",
    )
    _attributes = ("interface__name", "status", "device")
    _children = {}

    address: str
    namespace: str
    interface__name: str
    device: Optional[str]
    status: str
    uuid: Optional[UUID]


class Cable(DiffSyncModel):
    """Base Cable model."""

    _modelname = "cable"
    _identifiers = ("from_device", "from_interface", "to_device", "to_interface")
    _attributes = ()
    _children = {}

    from_device: str
    from_interface: str
    to_device: str
    to_interface: str
    uuid: Optional[UUID]


Building.update_forward_refs()
Room.update_forward_refs()
Namespace.update_forward_refs()
Prefix.update_forward_refs()
IPAddress.update_forward_refs()
VLANGroup.update_forward_refs()
VLAN.update_forward_refs()

# TODO: Implement base model(s) for cable interconnections between devices
