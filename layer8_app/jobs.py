"""Test jobs for the Layer 8 app."""

from nautobot.apps.jobs import ChoiceVar, Job, register_jobs

from .helpers.tenant_api import fetch_buildings_list, get_building_data
from .helpers.auvik_api import get_auvik_tenants

from .ssot_jobs.sync_tenant_api import BuildingDataSource

from .ssot_jobs.jobs import AuvikDataSource, Layer8DataSource

from .models import AuvikTenant

name = "Layer8 App Jobs"


class LoadBuildings(Job):
    """Class to provide a job that loads buildings from the Tenant API."""

    class Meta:
        """Metadata for the job."""

        name = "Load Buildings"
        description = "Load a building and it's rooms from the Tenant API and creates them as locations in Nautobot."

    building_id = ChoiceVar(description="Select a building to import", label="Building", choices=fetch_buildings_list)

    def run(self, building_id, get_building_data=get_building_data):
        """Run the job."""
        building_data = get_building_data(building_id)
        self.logger.info(f"Building Data: {building_data}")


class LoadAuvikTenants(Job):
    """Class to provide a job that loads Auvik tenants from the Auvik API."""

    class Meta:
        """Metadata for the job."""

        name = "Load Auvik Tenants"
        description = "Load Auvik tenants from the Auvik API and create them as AuvikTenant objects in Nautobot."

    def run(self):
        """Run the job."""
        self.logger.info("Loading Auvik tenants...")

        auvik_tenants = get_auvik_tenants()
        for tenant in auvik_tenants.data:
            domain_prefix = tenant.attributes.domain_prefix
            tenant_id = tenant.id

            AuvikTenant.objects.update_or_create(auvik_tenant_id=tenant_id, defaults={"name": domain_prefix})
            self.logger.info(f"Loaded Auvik tenant: {domain_prefix} ({tenant_id})")

        self.logger.info("Auvik tenants loaded successfully.")


jobs = [LoadAuvikTenants, LoadBuildings, BuildingDataSource, Layer8DataSource, AuvikDataSource]
register_jobs(*jobs)
