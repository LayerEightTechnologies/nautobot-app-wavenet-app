"""DiffSyncModel DCIM subclasses for Nautobot data sync."""

from nautobot.dcim.models import Location as OrmBuilding
from nautobot.dcim.models import LocationType as OrmLocationType
from nautobot.extras.models import Status as OrmStatus

from ..base.dcim import Building


class NautobotBuilding(Building):
    """Nautobot Building model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Building object in Nautobot."""
        diffsync.job.logger.info(f"Creating Building: {ids['name']}")
        loc_type = OrmLocationType.objects.get_or_create(name="Building")[0]
        status = OrmStatus.objects.get(name="Planned")
        new_building = OrmBuilding(name=ids["name"], status=status, location_type=loc_type)
        new_building.validated_save()
        if attrs.get("external_id"):
            new_building.custom_field_data.update({"external_id": attrs["external_id"]})
            new_building.validated_save()
        diffsync.building_map[ids["name"]] = new_building.id
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Building object in Nautobot."""
        _building = OrmBuilding.objects.get(id=self.uuid)
        self.diffsync.job.logger.info(f"Updating Building: {_building.name}")
        # No fields to update yet so just save
        _building.validated_save()
        return super().update(attrs)

    def delete(self):
        """Delete Building object in Nautobot."""
        _building = OrmBuilding.objects.get(id=self.uuid)
        self.diffsync.job.logger.info(f"Deleting Building: {_building.name}")
        _building.delete()
        return super().delete()
