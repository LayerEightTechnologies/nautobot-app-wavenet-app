"""Django models for the layer8_app app."""

from django.db import models

from nautobot.apps.models import BaseModel


class AuvikTenant(BaseModel):
    """Model for storing Auvik Tenant list."""

    name = models.CharField(max_length=255)
    auvik_tenant_id = models.CharField(unique=True, max_length=255)

    def __str__(self):
        """String representation of AuvikTenant."""
        return f"{self.name} ({self.auvik_tenant_id})"


class AuvikTenantBuildingRelationship(BaseModel):
    """Model for storing Auvik Tenant relationships to locations."""

    auvik_tenant = models.ForeignKey(
        "layer8_app.AuvikTenant",
        on_delete=models.CASCADE,
        related_name="auvik_tenants",
    )
    building = models.ForeignKey(
        "dcim.Location",
        on_delete=models.SET_NULL,
        null=True,
        related_name="buildings",
        limit_choices_to={"location_type__name": "Building"},
    )
