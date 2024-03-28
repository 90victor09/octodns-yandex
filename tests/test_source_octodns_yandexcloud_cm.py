import pytest
import yandexcloud
from yandex.cloud.certificatemanager.v1.certificate_service_pb2 import (
    ListCertificatesResponse,
)
from yandex.cloud.certificatemanager.v1.certificate_service_pb2_grpc import (
    CertificateServiceStub,
)

from octodns.zone import Zone

from octodns_yandex import YandexCloudCMSource
from octodns_yandex.auth import AUTH_TYPE_METADATA
from octodns_yandex.exception import YandexCloudConfigException
from tests.fixtures import STUB_FOLDER_ID
from tests.fixtures.certificates import (
    HTTP_CHALLENGE_CERTIFICATE,
    IMPORTED_CERTIFICATE,
    STUB_CERTIFICATE_1,
    STUB_CERTIFICATE_2,
    STUB_IDNA_CERTIFICATE,
)


class StubSDK:
    def __init__(self, *args, **kwargs):
        pass

    def client(self, *args):
        class StubChannel:
            def unary_unary(self, *args, **kwargs):
                pass

        return CertificateServiceStub(StubChannel())

    def wait_operation_and_get_result(self, *args, **kwargs):
        pass


@pytest.fixture()
def disable_sdk(monkeypatch):
    monkeypatch.setattr(yandexcloud, 'SDK', StubSDK)
    return None


@pytest.fixture()
def provider(disable_sdk):
    return YandexCloudCMSource(
        "test", folder_id=STUB_FOLDER_ID, auth_type=AUTH_TYPE_METADATA
    )


class TestYandexCloudCMSource:
    def test_config_error(self, disable_sdk):
        with pytest.raises(YandexCloudConfigException):
            YandexCloudCMSource(
                "test",
                folder_id=STUB_FOLDER_ID,
                record_type='NS',
                auth_type=AUTH_TYPE_METADATA,
            )

    def test_process_certificate_managed(self, provider, monkeypatch):
        zone = Zone('example.com.', [])

        # Not matching
        provider.process_certificate(zone, STUB_IDNA_CERTIFICATE)
        assert len(zone.records) == 0

        # Not managed
        provider.process_certificate(zone, IMPORTED_CERTIFICATE)
        assert len(zone.records) == 0

        # Wrong challenge type
        provider.process_certificate(zone, HTTP_CHALLENGE_CERTIFICATE)
        assert len(zone.records) == 0

        # Domain + wildcard = challenge duplicate
        provider.process_certificate(zone, STUB_CERTIFICATE_1)
        assert len(zone.records) == 1

        record = zone.records.pop()
        assert record._type == 'CNAME'
        assert record.name == '_acme-challenge'
        assert (
            record.data['value'] == 'fpqahphei3aegootoh0a.cm.yandexcloud.net.'
        )
        assert record.data['ttl'] == provider.record_ttl
        zone.remove_record(record)

        # Two domains
        provider.process_certificate(zone, STUB_CERTIFICATE_2)
        assert len(zone.records) == 2

        records = zone.records
        for i in range(2):
            record = records.pop()
            assert record._type == 'CNAME'
            assert record.name in [
                '_acme-challenge.cdn',
                '_acme-challenge.cdn2',
            ]
            assert (
                record.data['value']
                == 'fpqco0ongail3feejee1.cm.yandexcloud.net.'
            )
            assert record.data['ttl'] == provider.record_ttl
            zone.remove_record(record)

        # Two domains, only one matches zone
        provider.record_type = 'TXT'
        provider.record_ttl = 300
        zone = Zone('cdn.example.com.', [])
        provider.process_certificate(zone, STUB_CERTIFICATE_2)
        assert len(zone.records) == 1

        record = zone.records.pop()
        assert record._type == 'TXT'
        assert record.name == '_acme-challenge'
        assert (
            record.data['value']
            == 'DIzWSC8sf8Sh2iMMO7chYopq8aAiNhcuxINGDKvONEA'
        )
        assert record.data['ttl'] == provider.record_ttl

        # Test idna
        zone = Zone('xn--e1aybc.xn--p1ai.', [])
        provider.process_certificate(zone, STUB_IDNA_CERTIFICATE)
        assert len(zone.records) == 1

        record = zone.records.pop()
        assert record._type == 'TXT'
        assert record.name == '_acme-challenge'
        assert record.data['values'] == [
            'ShsQrb08EUXyAmJ2UVGs5LPZuoOJEwTTmhQRM5LRq9T',
            'r4joRe9NgOIhyYLbNOCxdSPXNjnuU95kD1VbYbM0sNd',
        ]
        assert record.data['ttl'] == provider.record_ttl
        zone.remove_record(record)

    def test_populate(self, provider, monkeypatch):
        def _list(req):
            if req.page_token == '':
                return ListCertificatesResponse(
                    next_page_token='123', certificates=[STUB_CERTIFICATE_1]
                )
            else:
                return ListCertificatesResponse(
                    next_page_token='', certificates=[STUB_IDNA_CERTIFICATE]
                )

        monkeypatch.setattr(provider, 'process_certificate', lambda *args: None)
        monkeypatch.setattr(provider.cm_service, 'List', _list)

        zone = Zone('example.com.', [])
        provider.populate(zone)
