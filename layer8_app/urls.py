from django.urls import path
from .views import CableCreateView

app_name = "layer8_app"

urlpatterns = [
    path("cable/create/", CableCreateView.as_view(), name="cable_create"),
]