"""DiffSync adatper for Layer8."""

from diffsync import DiffSync
from diffsync.exceptions import ObjectAlreadyExists
from ..models.base import dcim


class Layer8Adapter(DiffSync):
    """DiffSync adapter using openapi_client to communicate to Layer8 API."""

    building = dcim.Building
    room = dcim.Room

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

    def load_rooms(self):
        """Load Layer8 rooms."""
        self.job.logger.info(f"Loading rooms...")
        response = self.layer8.get_rooms_with_building(page_size=10000, is_active=True)
        for record in response["rooms"]["items"]:
            if (
                record["building"]
                and record["building"]["status"] == "Live Building"
                and record["building"]["dead"] is not True
            ):
                if self.job.debug:
                    self.job.logger.info(
                        f"Loading Room from Layer8: {record['room_number']} ({record['building']['building_name']})"
                    )
                room = self.room(
                    name=record["room_number"],
                    status__name="Planned",
                    external_id=record["id"],
                    parent__name=record["building"]["building_name"],
                    uuid=None,
                )
                try:
                    _building = self.get(self.building, record["building"]["building_name"])
                    if self.job.debug:
                        self.job.logger.info(
                            f"Loaded Room from Layer8 with data: {room.name} - {room.status__name} - {room.external_id} - {room.parent__name}"
                        )
                    if _building:
                        self.add(room)
                        _building.add_child(child=room)
                    else:
                        if self.job.debug:
                            self.job.logger.info(f"Building {record['building']['building_name']} not found, skipping")
                except ObjectAlreadyExists as err:
                    if self.job.debug:
                        self.job.logger.info(f"Room already exists: {err}")
            else:
                if self.job.debug:
                    self.job.logger.info(f"Room {record['room_number']} is not in a live building, skipping")

    def load(self):
        """Load data from Layer8."""
        self.load_buildings()
        self.load_rooms()
