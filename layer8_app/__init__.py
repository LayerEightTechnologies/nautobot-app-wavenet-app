"""App declaration for layer8_app."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class Layer8AppConfig(NautobotAppConfig):
    """App configuration for the layer8_app app."""

    name = "layer8_app"
    verbose_name = "Wavenet App"
    version = __version__
    author = "Layer8 Technologies Ltd"
    description = "Wavenet App for synchronising data between Tenant API, Auvik and Nautobot."
    base_url = "layer8-app"
    required_settings = []
    min_version = "2.0.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}
    jobs = "jobs.jobs"


config = Layer8AppConfig  # pylint:disable=invalid-name
