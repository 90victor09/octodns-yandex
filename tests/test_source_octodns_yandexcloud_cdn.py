import pytest
import yandexcloud
from yandex.cloud.cdn.v1.resource_service_pb2 import (
    GetProviderCNameResponse,
    ListResourcesResponse,
)
from yandex.cloud.cdn.v1.resource_service_pb2_grpc import ResourceServiceStub

from octodns.record import Record
from octodns.zone import Zone

from octodns_yandex import YandexCloudCDNSource
from octodns_yandex.auth import AUTH_TYPE_METADATA
from tests.fixtures import STUB_FOLDER_ID
from tests.fixtures.cdn_resources import (
    STUB_CDN_RESOURCE_1,
    STUB_CDN_RESOURCE_2,
)


class StubSDK:
    def __init__(self, *args, **kwargs):
        pass

    def client(self, *args):
        class StubChannel:
            def unary_unary(self, *args, **kwargs):
                pass

        return ResourceServiceStub(StubChannel())

    def wait_operation_and_get_result(self, *args, **kwargs):
        pass


@pytest.fixture()
def disable_sdk(monkeypatch):
    monkeypatch.setattr(yandexcloud, 'SDK', StubSDK)
    return None


@pytest.fixture()
def provider(disable_sdk):
    return YandexCloudCDNSource(
        "test", folder_id=STUB_FOLDER_ID, auth_type=AUTH_TYPE_METADATA
    )


class TestYandexCloudCDNSource:
    def test_get_provider_cname(self, provider, monkeypatch):
        monkeypatch.setattr(
            provider.cdn_service,
            'GetProviderCName',
            lambda *args: GetProviderCNameResponse(cname='test.com'),
        )
        assert provider.get_provider_cname() == 'test.com.'
        monkeypatch.undo()

        def raise_exc(*args):
            raise Exception("Failed")

        monkeypatch.setattr(provider.cdn_service, 'GetProviderCName', raise_exc)
        assert provider.get_provider_cname() == 'test.com.'

    def test_get_provider_cname_with_dot(self, provider, monkeypatch):
        monkeypatch.setattr(
            provider.cdn_service,
            'GetProviderCName',
            lambda *args: GetProviderCNameResponse(cname='test.com.'),
        )
        assert provider.get_provider_cname() == 'test.com.'

    def test_process_resource(self, provider, monkeypatch):
        zone = Zone('example.com.', [])

        CDN_PROVIDER_CNAME = 'test.com.'
        monkeypatch.setattr(
            provider, 'get_provider_cname', lambda *args: CDN_PROVIDER_CNAME
        )

        MAIN_RECORD = Record.new(
            zone,
            'cdn',
            data={
                'type': 'CNAME',
                'ttl': provider.record_ttl,
                'value': CDN_PROVIDER_CNAME,
            },
        )
        SECONDARY_RECORD = Record.new(
            zone,
            'cdn2',
            data={
                'type': 'CNAME',
                'ttl': provider.record_ttl,
                'value': CDN_PROVIDER_CNAME,
            },
        )

        provider.process_resource(zone, STUB_CDN_RESOURCE_1)
        assert len(zone.records) == 1
        assert zone.records.pop() == MAIN_RECORD
        zone.remove_record(MAIN_RECORD)

        provider.process_resource(zone, STUB_CDN_RESOURCE_2)
        assert len(zone.records) == 2
        assert next((r for r in zone.records if r.name == 'cdn')) == MAIN_RECORD
        assert (
            next((r for r in zone.records if r.name == 'cdn2'))
            == SECONDARY_RECORD
        )

    def test_populate(self, provider, monkeypatch):
        def _list(req):
            if req.page_token == '':
                return ListResourcesResponse(
                    next_page_token='123', resources=[STUB_CDN_RESOURCE_1]
                )
            else:
                return ListResourcesResponse(
                    next_page_token='', resources=[STUB_CDN_RESOURCE_2]
                )

        monkeypatch.setattr(provider, 'process_resource', lambda *args: None)
        monkeypatch.setattr(provider.cdn_service, 'List', _list)

        zone = Zone('example.com.', [])
        provider.populate(zone)
