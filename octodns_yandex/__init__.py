#
#
#
from .record import YandexCloudAnameRecord
from .yandexcloud_provider import YandexCloudProvider
from .version import __VERSION__, __version__

__all__ = [
    YandexCloudProvider,
    YandexCloudAnameRecord
]

# quell warnings
__VERSION__
__version__
