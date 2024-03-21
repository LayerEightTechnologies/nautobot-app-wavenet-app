"""DiffSync adapter class for Nautobot as a source of truth."""

from collections import defaultdict

from diffsync import DiffSync
from diffsync.exceptions import ObjectAlreadyExists
from nautobot.dcim.models import Location, LocationType
from nautobot.ipam.models import Namespace
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

    namespace = dcim.Namespace

    top_level = ("namespace",)

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

    def load_namespaces(self):
        """Load namespace for building."""
        try:
            building_name = Location.objects.get(
                id=AuvikTenantBuildingRelationship.objects.get(auvik_tenant=self.job.building_to_sync).building.id
            )
        except Location.DoesNotExist:
            self.job.logger.error(f"Building ID {self.building_id} does not exist in Nautobot.")
            return

        try:
            _namespace = Namespace.objects.get(name=building_name)

            namespace = self.namespace(
                name=_namespace.name,
                description=_namespace.description,
            )
            self.add(namespace)
        except ObjectAlreadyExists as err:
            self.job.logger.info(f"Namespace already exists: {err}")

        except Namespace.DoesNotExist:
            self.job.logger.info(f"Namespace does not exist in Nautobot. Not adding")

    def load(self):
        """Load data from Nautobot."""
        self.load_namespaces()
