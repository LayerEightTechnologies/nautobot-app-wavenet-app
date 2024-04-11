"""Test jobs for the Layer 8 app."""

from nautobot.apps.jobs import ChoiceVar, Job, register_jobs

from .helpers.tenant_api import fetch_buildings_list, get_building_data
from .helpers.auvik_api import get_auvik_tenants, auvik_api, auvik_api_device, fetch_all_pages

# from .ssot_jobs.sync_tenant_api import BuildingDataSource

from .ssot_jobs.jobs import AuvikDataSource, Layer8DataSource

from .models import AuvikTenant, AuvikDeviceVendors, AuvikDeviceModels

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


class LoadAuvikVendorsAndModels(Job):
    """Class to provide a job that loads Auvik vendors from the Auvik API."""

    class Meta:
        """Metadata for the job."""

        name = "Load Auvik Device Vendors and Models"
        description = "Load Auvik device vendors and models from the Auvik API and create them as AuvikDeviceVendors and AuvikDeviceModels objects in Nautobot."

    tenants_list = AuvikTenant.objects.all()
    # tenants_choices = [(tenant.auvik_tenant_id, tenant.name) for tenant in tenants_list]
    tenant_choices = [("1", "Test Tenant")]
    auvik_tenant_id = ChoiceVar(
        description="Select an Auvik tenant to import", label="Auvik Tenant", choices=tenants_choices
    )

    def run(self, auvik_tenant_id=None):
        """Run the job."""
        self.logger.info("Loading Auvik device vendors and models...")

        auvik_api_instance = auvik_api_device(auvik_api())
        try:
            auvik_tenant = AuvikTenant.objects.get(auvik_tenant_id=auvik_tenant_id)
            self.logger.info(f"Using Auvik tenant {auvik_tenant.name} with ID: {auvik_tenant.auvik_tenant_id}")
        except AuvikTenant.DoesNotExist:
            self.logger.error("Auvik tenant not found.")
            return

        params = {"tenants": auvik_tenant_id}

        try:
            auvik_devices = fetch_all_pages(auvik_api_instance, "read_multiple_device_info", **params)
        except Exception as e:
            self.logger.error(f"Failed to fetch Auvik devices: {e}")
            return

        vendor_names = []
        make_models = []

        for device in auvik_devices:
            vendor_name = getattr(device.attributes, "vendor_name", None)
            make_model = getattr(device.attributes, "make_model", None)

            if vendor_name not in vendor_names and vendor_name is not None:
                vendor_names.append(vendor_name)
                self.logger.info(f"Loaded Auvik device vendor: {vendor_name}")

            if make_model not in make_models and make_model is not None:
                make_models.append(make_model)
                self.logger.info(f"Loaded Auvik device model: {make_model}")

        for vendor in vendor_names:
            try:
                AuvikDeviceVendors.objects.update_or_create(
                    auvik_vendor_name=vendor, defaults={"auvik_vendor_name": vendor}
                )
                self.logger.info(f"Added/updated Auvik device vendor in Nautobot: {vendor}")
            except Exception as e:
                self.logger.error(f"Failed to add/update Auvik device vendor in Nautobot: {e}")

        for model in make_models:
            try:
                AuvikDeviceModels.objects.update_or_create(auvik_model_name=model, defaults={"auvik_model_name": model})
                self.logger.info(f"Added/updated Auvik device model in Nautobot: {model}")
            except Exception as e:
                self.logger.error(f"Failed to add/update Auvik device model in Nautobot: {e}")

        self.logger.info("Auvik device vendors and models loaded successfully.")


jobs = [
    LoadAuvikTenants,
    # LoadBuildings,
    # BuildingDataSource,
    Layer8DataSource,
    AuvikDataSource,
    LoadAuvikVendorsAndModels,
]
register_jobs(*jobs)
