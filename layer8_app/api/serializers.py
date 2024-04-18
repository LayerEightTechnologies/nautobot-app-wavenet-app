"""Serializers for the Auvik integration app."""

from nautobot.apps.api import ValidatedModelSerializer, NautobotModelSerializer
from ..models import AuvikTenantBuildingRelationship, AuvikTenant


class AuvikTenantBuildingRelationshipSerializer(NautobotModelSerializer):
    """Serializer for the AuvikTenantBuildingRelationship model."""

    class Meta:
        """Metadata for the serializer."""

        model = AuvikTenantBuildingRelationship
        fields = "__all__"


class AuvikTenantSerializer(NautobotModelSerializer):
    """Serializer for the AuvikTenant model."""

    class Meta:
        """Metadata for the serializer."""

        model = AuvikTenant
        fields = "__all__"
