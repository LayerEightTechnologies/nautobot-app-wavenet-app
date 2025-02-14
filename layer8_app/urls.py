from django.urls import path
from .views import CableCreateView, ExpandableCableCreateView, PatchPanelCreateView

app_name = "layer8_app"

urlpatterns = [
    path("cable/create/", CableCreateView.as_view(), name="cable_create"),
    path("cable/create-expandable/", ExpandableCableCreateView.as_view(), name="cable_create_expandable"),
    path("patchpanel/create/", PatchPanelCreateView.as_view(), name="patch_panel_create"),
]
