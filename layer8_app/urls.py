from django.urls import path
from .views import CableCreateView, PatchPanelCreateView

app_name = "layer8_app"

urlpatterns = [
    path("cable/create/", CableCreateView.as_view(), name="cable_create"),
    path("patchpanel/create/", PatchPanelCreateView.as_view(), name="patch_panel_create"),
]