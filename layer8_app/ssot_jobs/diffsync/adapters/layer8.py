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
            _longitude = None
            _latitude = None
            if record["coordinate"] and record["coordinate"]["coordinates"] and record["coordinate"]["coordinates"][1]:
                _longitude = float("{:.6f}".format(record["coordinate"]["coordinates"][1]))
                _latitude = float("{:.6f}".format(record["coordinate"]["coordinates"][0]))
            _status = "Planned"
            if record["status"] == "Old Building":
                _status = "Retired"
            building = self.building(
                name=record["building_name"],
                # Potentially remove status from here, so it's not included in DiffSync. We always set the status for a new building to "Planned",
                # and we don't want to update the status of existing buildings.
                status__name=_status,  # note, we always set the status for a new building to "Planned"
                external_id=record["id"],
                uuid=None,
                longitude=_longitude,
                latitude=_latitude,
                technical_reference=(record["wifi_id"] or None),
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
                # Room Status should be set to "Planned" for new rooms, and "Retired" for rooms that are no longer active.
                # For existing rooms, we don't want to update the status. How can we achieve this?
                # Probably handled in the DiffSync model, where we only set the status to planned for new objects, otherwise we set it to
                # the existing status or Retired based on the below.
                _status = "Planned"
                if record["is_active"] == False:
                    _status = "Retired"
                room = self.room(
                    name=record["room_number"],
                    status__name=_status,
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
