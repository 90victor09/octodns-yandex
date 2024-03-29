from importlib.metadata import PackageNotFoundError, version

from octodns import __VERSION__ as octodns_version

# TODO: remove __VERSION__ with the next major version.py release
__version__ = __VERSION__ = '0.0.3'

try:
    yandexcloud_version = version("yandexcloud")
except PackageNotFoundError:
    yandexcloud_version = "0.0.0"


def get_base_user_agent():
    return f"octodns/{octodns_version} octodns-yandex/{__version__}"


def get_user_agent():
    return (
        f"{get_base_user_agent()} yandex-cloud-python-sdk/{yandexcloud_version}"
    )
