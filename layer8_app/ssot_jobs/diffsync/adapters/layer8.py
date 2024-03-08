"""DiffSync adatper for Layer8."""

from diffsync import DiffSync
from diffsync.exceptions import ObjectAlreadyExists
from ..models.base import dcim


class Layer8Adapter(DiffSync):
    """DiffSync adapter using openapi_client to communicate to Layer8 API."""

    building = dcim.Building

    top_level = ("building",)

    def __init__(self, *args, job, sync=None, api_client, **kwargs):
        """Initialize Layer8Adapter."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
        self.layer8 = api_client

    def load_buildings(self):
        """Load Layer8  buildings."""
        response = self.layer8.get_buildings(page_size=1000, status="Live Building")
        for record in response["buildings"]["items"]:
            self.job.logger.info(f"Loading Building: {record['building_name']}")
            building = self.building(
                name=record["building_name"],
                status__name="Planned",
                external_id=record["id"],
                uuid=None,
            )
            try:
                self.add(building)
            except ObjectAlreadyExists as err:
                self.job.logger.info(f"Building already exists: {err}")

    def load(self):
        """Load data from Layer8."""
        self.load_buildings()
