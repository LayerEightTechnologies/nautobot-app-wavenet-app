"""Layer8 App Admin interface."""

from django.contrib import admin
from nautobot.apps.admin import NautobotModelAdmin

from .models import AuvikTenant, AuvikTenantBuildingRelationship


@admin.register(AuvikTenant)
class AuvikTenantAdmin(NautobotModelAdmin):
    """Admin interface for AuvikTenant."""

    list_display = ("name", "auvik_tenant_id")


@admin.register(AuvikTenantBuildingRelationship)
class AuvikTenantBuildingRelationshipsAdmin(NautobotModelAdmin):
    """Admin interface for AuvikTenantBuildingRelationships."""

    list_display = ("auvik_tenant", "building")
