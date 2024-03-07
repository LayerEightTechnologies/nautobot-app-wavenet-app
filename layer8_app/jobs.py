"""Test jobs for the Layer 8 app."""

from nautobot.apps.jobs import ChoiceVar, Job, register_jobs

from .helpers.tenant_api import fetch_buildings_list, get_building_data

from .ssot_jobs.sync_tenant_api import BuildingDataSource

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


jobs = [LoadBuildings, BuildingDataSource]
register_jobs(*jobs)
