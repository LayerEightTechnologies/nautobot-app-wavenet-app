"""API views for the AuvikTenantBuildingRelationship model."""

from rest_framework.viewsets import ModelViewSet
from nautobot.apps.api import NautobotModelViewSet

from ..models import AuvikTenantBuildingRelationship, AuvikTenant
from .serializers import AuvikTenantBuildingRelationshipSerializer, AuvikTenantSerializer


class AuvikTenantBuildingRelationshipViewSet(NautobotModelViewSet):
    """API view for AuvikTenantBuildingRelationship objects."""

    queryset = AuvikTenantBuildingRelationship.objects.all()
    serializer_class = AuvikTenantBuildingRelationshipSerializer


class AuvikTenantViewSet(NautobotModelViewSet):
    """API view for AuvikTenant objects."""

    queryset = AuvikTenant.objects.all()
    serializer_class = AuvikTenantSerializer
