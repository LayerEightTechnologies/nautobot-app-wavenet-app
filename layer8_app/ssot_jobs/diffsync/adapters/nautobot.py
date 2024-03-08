"""DiffSync adapter class for Nautobot as a source of truth."""

from collections import defaultdict

from diffsync import DiffSync
from diffsync.exceptions import ObjectAlreadyExists
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status

from ..models.nautobot import dcim


class NautobotAdapter(DiffSync):
    """Nautobot adapter for DiffSync."""

    building = dcim.NautobotBuilding

    top_level = ("building",)

    building_map = {}

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
                    external_id=int(building.id),
                )
                if self.job.debug:
                    self.job.logger.info(
                        f"Loaded Building with data: {building.name} - {building.status__name} - {building.external_id}"
                    )
                self.add(building)
            except AttributeError as err:
                self.job.logger.warning(f"Failed to load {building.name}: {err}")
                continue

    def load(self):
        """Load data from Nautobot."""
        self.load_buildings()
