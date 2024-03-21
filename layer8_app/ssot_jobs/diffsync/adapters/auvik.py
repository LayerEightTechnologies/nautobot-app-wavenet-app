"""DiffSync adatper for Layer8."""

from diffsync import DiffSync
from diffsync.exceptions import ObjectAlreadyExists
from ..models.base import dcim
from nautobot.dcim.models import Location
from ....models import AuvikTenantBuildingRelationship


class AuvikAdapter(DiffSync):
    """DiffSync adapter using layer8_auvik_api_client to communicate to Auvik API."""

    namespace = dcim.Namespace
    vlangroup = dcim.VLANGroup
    vlan = dcim.VLAN
    prefix = dcim.Prefix
    ipaddr = dcim.IPAddress

    top_level = ("namespace",)

    def __init__(self, *args, job, sync=None, api_client, building_id, **kwargs):
        """Initialize AuvikAdapter."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
        self.auvik = api_client
        self.building_id = building_id

    def load_namespaces(self):
        """Load namespace for building."""
        self.job.logger.info(f"auvik_tenant_id: {self.job.building_to_sync}")
        try:
            building_name = Location.objects.get(
                id=AuvikTenantBuildingRelationship.objects.get(auvik_tenant=self.job.building_to_sync).building.id
            )
            if self.job.debug:
                self.job.logger.info(f"Building Name: {building_name}")
        except Location.DoesNotExist:
            self.job.logger.error(f"Building ID {self.building_id} does not exist in Nautobot.")
            return

        namespace = self.namespace(
            name=f"{building_name}",
            description=f"{building_name} namespace",
        )
        try:
            self.add(namespace)
        except ObjectAlreadyExists as err:
            self.job.logger.info(f"Namespace already exists: {err}")

    def load(self):
        """Load data from Auvik."""
        self.load_namespaces()
