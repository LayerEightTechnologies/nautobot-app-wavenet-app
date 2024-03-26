"""DiffSync adapter class for Nautobot as a source of truth."""

from collections import defaultdict

from diffsync import DiffSync
from diffsync.exceptions import ObjectAlreadyExists
from nautobot.dcim.models import Location, LocationType, Device
from nautobot.ipam.models import Namespace, VLANGroup, VLAN, Prefix
from nautobot.extras.models import Status

from ..models.nautobot import dcim
from ....models import AuvikTenantBuildingRelationship


class NautobotAdapter(DiffSync):
    """Nautobot adapter for Layer8 DiffSync."""

    building = dcim.NautobotBuilding
    room = dcim.NautobotRoom

    top_level = ("building",)

    building_map = {}
    room_map = {}

    def __init__(self, *args, job, sync=None, **kwargs):
        """Initialize the Nautobot DiffSync adapter."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
        self.objects_to_delete = defaultdict(list)

    def sync_complete(self, source: DiffSync, *args, **kwargs):
        """Clean up function for DiffSync sync.

        Deletes objects from Nautobot that need to be deleted in a specific order.
        """
        return super().sync_complete(source, *args, **kwargs)

    def load_buildings(self):
        """Add Nautobot Location objects as DiffSync Building models."""
        for building in Location.objects.filter(location_type=LocationType.objects.get_or_create(name="Building")[0]):
            self.building_map[building.name] = building.id
            try:
                building = self.building(
                    name=building.name,
                    uuid=building.id,
                    status__name=building.status.name,
                    external_id=int(building.custom_field_data.get("external_id")),
                    longitude=building.longitude,
                    latitude=building.latitude,
                    technical_reference=(building.custom_field_data.get("technical_reference") or None),
                )
                if self.job.debug:
                    self.job.logger.info(
                        f"Loaded Building with data: {building.name} - {building.status__name} - {building.external_id}"
                    )
                self.add(building)
            except AttributeError as err:
                self.job.logger.warning(f"Failed to load {building.name}: {err}")
                continue

    def load_rooms(self):
        """Add Nautobot Location objects as DiffSync Room models."""
        for _room in Location.objects.filter(location_type=LocationType.objects.get_or_create(name="Room")[0]):
            if _room.parent.name not in self.room_map:
                self.room_map[_room.parent.name] = {}
            if _room.name not in self.room_map[_room.parent.name]:
                self.room_map[_room.parent.name][_room.name] = {}
            self.room_map[_room.parent.name][_room.name] = _room.id
            if _room.parent is not None:
                building_id = self.building_map.get(_room.parent.name)
                if building_id is not None:
                    try:
                        room = dcim.NautobotRoom(
                            name=_room.name,
                            uuid=_room.id,
                            status__name=_room.status.name,
                            external_id=int(_room.custom_field_data.get("external_id")),
                            parent__name=_room.parent.name,
                        )
                        if self.job.debug:
                            self.job.logger.info(
                                f"Loaded Room from Nautobot with data: {room.name} - {room.status__name} - {room.external_id} - {room.parent__name}"
                            )
                        self.add(room)
                        _building = self.get(self.building, _room.parent.name)
                        _building.add_child(child=room)
                    except AttributeError as err:
                        self.job.logger.warning(f"Failed to load {room.name}: {err}")
                        continue

    def load(self):
        """Load data from Nautobot."""
        self.load_buildings()
        self.load_rooms()


class NautobotAuvikAdapter(DiffSync):
    """Nautobot adapter for Auvik diffsync."""

    namespace = dcim.NautobotNamespace
    vlangroup = dcim.NautobotVLANGroup
    vlan = dcim.NautobotVLAN
    prefix = dcim.NautobotPrefix
    device = dcim.NautobotDevice
    interface = dcim.NautobotInterface
    ipaddr = dcim.NautobotIPAddress

    top_level = (
        "namespace",
        "vlangroup",
        "device",
    )

    def __init__(self, *args, job, sync=None, **kwargs):
        """Initialize the Nautobot DiffSync adapter."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
        self.objects_to_delete = defaultdict(list)
        try:
            self.building_name = Location.objects.get(
                id=AuvikTenantBuildingRelationship.objects.get(auvik_tenant=self.job.building_to_sync).building.id
            )
        except Location.DoesNotExist:
            self.job.logger.error(f"Building ID {self.building_id} does not exist in Nautobot.")
            self.building_name = None
            return

    def sync_complete(self, source: DiffSync, *args, **kwargs):
        """Clean up function for DiffSync sync.

        Deletes objects from Nautobot that need to be deleted in a specific order.
        """
        return super().sync_complete(source, *args, **kwargs)

    def load_namespaces(self):
        """Load namespace for building from Nautobot."""
        try:
            _namespace = Namespace.objects.get(name=self.building_name)

            namespace = self.namespace(
                name=_namespace.name,
                description=_namespace.description,
            )
            self.add(namespace)
            if self.job.debug:
                self.job.logger.info(f"Added Nautobot Namespace: ```{namespace.__dict__}```")
        except ObjectAlreadyExists as err:
            if self.job.debug:
                self.job.logger.info(f"Namespace already exists: {err}")
        except Namespace.DoesNotExist:
            if self.job.debug:
                self.job.logger.info(f"Namespace for {self.building_name} does not exist in Nautobot. Not loading.")

    def load_vlangroups(self):
        """Load VLAN Groups for building from Nautobot."""
        try:
            vlangroup_name = f"{self.building_name} VLANs"
            _vlangroup = VLANGroup.objects.get(name=vlangroup_name, location__name=self.building_name)

            vlangroup = self.vlangroup(
                name=_vlangroup.name,
                location__name=self.building_name.name,
            )
            self.add(vlangroup)
            if self.job.debug:
                self.job.logger.info(f"Added Nautobot VLAN Group: ```{vlangroup.__dict__}```")
        except ObjectAlreadyExists as err:
            if self.job.debug:
                self.job.logger.info(f"VLAN Group already exists: {err}")
        except VLANGroup.DoesNotExist:
            if self.job.debug:
                self.job.logger.info(f"VLAN Group for {self.building_name} does not exist in Nautobot. Not loading.")

    def load_vlans(self):
        """Load VLANs for building from Nautobot."""
        try:
            vlans = VLAN.objects.filter(vlan_group=VLANGroup.objects.get(name=f"{self.building_name} VLANs"))
        except VLANGroup.DoesNotExist:
            if self.job.debug:
                self.job.logger.info(f"VLAN Group for {self.building_name} does not exist in Nautobot. No VLANs found.")
            return
        for _vlan in vlans:
            if _vlan.location is None:
                location = None
            else:
                location = _vlan.location.name
            vlan = self.vlan(
                name=_vlan.name,
                vid=_vlan.vid,
                vlangroup=_vlan.vlan_group.name,
                location__name=location,
            )
            try:
                self.add(vlan)
                _vlangroup = self.get(self.vlangroup, _vlan.vlan_group.name)
                _vlangroup.add_child(child=vlan)
                if self.job.debug:
                    self.job.logger.info(f"Added Nautobot VLAN: ```{vlan.__dict__}```")
            except ObjectAlreadyExists as err:
                if self.job.debug:
                    self.job.logger.info(f"VLAN already exists: {err}")

    def load_prefixes(self):
        """Load Prefixes for building from Nautobot."""
        try:
            namespace = Namespace.objects.get(name=self.building_name)
            prefixes = Prefix.objects.filter(namespace=namespace)
        except Namespace.DoesNotExist:
            if self.job.debug:
                self.job.logger.info(f"Namespace for {self.building_name} does not exist in Nautobot. Not loading.")
            return

        for _prefix in prefixes:
            prefix = self.prefix(
                prefix=_prefix.prefix.__str__(),
                namespace=_prefix.namespace.name,
                type=_prefix.type,
                status=_prefix.status.name,
                description=_prefix.description,
            )
            try:
                self.add(prefix)
                _namespace = self.get(self.namespace, _prefix.namespace.name)
                _namespace.add_child(child=prefix)
                if self.job.debug:
                    self.job.logger.info(f"Added Nautobot Prefix: ```{prefix.__dict__}```")
            except ObjectAlreadyExists as err:
                if self.job.debug:
                    self.job.logger.info(f"Prefix already exists: {err}")

    def load_devices(self):
        """Load devices for building from Nautobot."""
        try:
            building = Location.objects.get(name=self.building_name)
        except Location.DoesNotExist:
            if self.job.debug:
                self.job.logger.info(f"Building {self.building_name} does not exist in Nautobot. Not loading devices.")
            return

        devices = Device.objects.filter(location=building)
        for _device in devices:
            device = self.device(
                name=_device.name,
                location__name=_device.location.name,
                status__name=_device.status.name,
                serial=_device.serial,
                device_type=_device.device_type.model,
                manufacturer=_device.device_type.manufacturer.name,
                monitoring_profile=_device.custom_field_data.get("monitoring_profile"),
                role=_device.role.name,
            )

            try:
                self.add(device)
                if self.job.debug:
                    self.job.logger.info(f"Added Nautobot Device: ```{device.__dict__}```")
            except ObjectAlreadyExists as err:
                if self.job.debug:
                    self.job.logger.info(f"Device already exists: {err}")

            # Load management interface for device
            try:
                _interface = _device.interfaces.get(name="mgmt0")
                if _interface is not None:
                    interface = self.interface(
                        name=_interface.name,
                        description=_interface.description,
                        device__name=_device.name,
                        device__location__name=_device.location.name,
                        type=_interface.type,
                        status=_interface.status.name,
                        mgmt_only=_interface.mgmt_only,
                    )
                    self.add(interface)
                    device.add_child(child=interface)
            except:
                if self.job.debug:
                    self.job.logger.info(f"Device {device.name} does not have a management interface. Not loading.")

            # Load management IP address for device
            try:
                _ipaddr = _interface.ip_addresses.get(interface=_interface, address__contains=".")
                if _ipaddr is not None:
                    ipaddr = self.ipaddr(
                        address=_ipaddr.address,
                        namespace=_ipaddr.namespace.name,
                        interface__name=_interface.name,
                        status=_ipaddr.status.name,
                        device=_device.name,
                    )
                    self.add(ipaddr)
                    interface.add_child(child=ipaddr)
            except:
                if self.job.debug:
                    self.job.logger.info(f"Device {device.name} does not have a management IP address. Not loading.")

    # def load_interfaces(self):
    #     """
    #     Load interfaces for devices from Nautobot.

    #     Loads only one interface per device. The interface will be the management interface for the device.
    #     """
    #     pass

    # def load_ipaddrs(self):
    #     """
    #     Load IP addresses for interfaces from Nautobot.

    #     Loads only one IP address per interface. The IP address will be the management IP address for the device.
    #     """
    #     pass

    # TODO: Implement (parent) load_devices, (-> child) load_interfaces (mgmt if) and (-> child) load_ipaddrs (mgmt ip) methods
    # Load only one interface per device. The interface will be the management interface for the device.
    # The interface will be called "ManagementInterface" and will have the name "mgmt0"
    # The interface will have a single IP address, which will be the management IP address for the device
    # How are we going to identify the management IP address from Auvik?

    def load(self):
        """Load data from Nautobot."""
        self.load_namespaces()
        self.load_vlangroups()
        self.load_vlans()
        self.load_prefixes()
        self.load_devices()
