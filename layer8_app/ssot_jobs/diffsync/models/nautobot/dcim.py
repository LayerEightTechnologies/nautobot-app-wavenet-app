"""DiffSyncModel DCIM subclasses for Nautobot data sync."""

from django.core.exceptions import ValidationError

from nautobot.dcim.models import Location as OrmLocation
from nautobot.dcim.models import LocationType as OrmLocationType
from nautobot.extras.models import Status as OrmStatus

from ..base.dcim import Building
from ..base.dcim import Room


class NautobotBuilding(Building):
    """Nautobot Building model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Building object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating Building: {ids['name']}")
        loc_type = OrmLocationType.objects.get_or_create(name="Building")[0]
        status = OrmStatus.objects.get(name="Planned")
        new_building = OrmLocation(name=ids["name"], status=status, location_type=loc_type)
        new_building.validated_save()
        if attrs.get("external_id"):
            new_building.custom_field_data.update({"external_id": attrs["external_id"]})
            new_building.validated_save()
        diffsync.building_map[ids["name"]] = new_building.id
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Building object in Nautobot."""
        _building = OrmLocation.objects.get(id=self.uuid)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Updating Building: {_building.name}")
        # No fields to update yet so just save
        _building.validated_save()
        return super().update(attrs)

    def delete(self):
        """Delete Building object in Nautobot."""
        _building = OrmLocation.objects.get(id=self.uuid)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Deleting Building: {_building.name}")
        _building.delete()
        return super().delete()


class NautobotRoom(Room):
    """Nautobot Room model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Room object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating Room: {ids['name']}")
        try:
            loc_type = OrmLocationType.objects.get_or_create(name="Room")[0]
            status = OrmStatus.objects.get(name="Planned")
            new_room = OrmLocation(name=ids["name"], status=status, location_type=loc_type)
            # new_room.validated_save()
            if ids.get("external_id"):
                new_room.custom_field_data.update({"external_id": ids["external_id"]})
                # new_room.validated_save()
            if ids.get("parent__name"):
                parent = OrmLocation.objects.get(name=ids["parent__name"])
                new_room.parent = parent
                # new_room.validated_save()
            new_room.validated_save()
            if ids["parent__name"] not in diffsync.room_map:
                diffsync.room_map[ids["parent__name"]] = {}
            diffsync.room_map[ids["parent__name"]][ids["name"]] = new_room.id
        except ValidationError as e:
            diffsync.job.logger.error(
                f"Failed to create Room: {e} - {ids['name']} - {ids['parent__name']} - {ids['external_id']}"
            )
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Room object in Nautobot."""
        _room = OrmLocation.objects.get(id=self.uuid)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Updating Room: {_room.name}")
        # No fields to update yet so just save
        _room.validated_save()
        return super().update(attrs)

    def delete(self):
        """Delete Room object in Nautobot."""
        _room = OrmLocation.objects.get(id=self.uuid)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Deleting Room: {_room.name}")
        _room.delete()
        return super().delete()
