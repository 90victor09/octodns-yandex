#
#
#
import json
import subprocess
import tempfile

import grpc
import pytest
import yandexcloud
from yandex.cloud.dns.v1.dns_zone_pb2 import RecordSet
from yandex.cloud.dns.v1.dns_zone_service_pb2 import (
    ListDnsZoneRecordSetsResponse,
    ListDnsZonesResponse,
)
from yandex.cloud.dns.v1.dns_zone_service_pb2_grpc import DnsZoneServiceStub

from octodns.idna import idna_decode
from octodns.provider.plan import Plan
from octodns.record import Create, Delete, Update
from octodns.zone import Zone

from octodns_yandex import YandexCloudProvider
from octodns_yandex.yandexcloud_provider import (
    AUTH_TYPE_IAM,
    AUTH_TYPE_METADATA,
    AUTH_TYPE_OAUTH,
    AUTH_TYPE_SA_KEY,
    AUTH_TYPE_YC_CLI,
    YandexCloudConfigException,
    YandexCloudException,
    map_octodns_to_rset,
    map_rset_to_octodns,
)
from tests.fixtures.dns_zones import (
    STUB_FOLDER_ID,
    STUB_IDNA_ZONE,
    STUB_IDNA_ZONE_NAME,
    STUB_ZONE_1,
    STUB_ZONE_2,
    STUB_ZONE_NAME,
    STUB_ZONE_PUBLIC,
)
from tests.fixtures.record_sets import STUB_RECORDS

STUB_TOKEN = "token"
STUB_SA_KEY = {
    'id': 'id',
    'service_account_id': 'sa_id',
    'private_key': 'base64',
}


class StubSDK:
    def __init__(self, *args, **kwargs):
        pass

    def client(self, *args):
        class StubChannel:
            def unary_unary(self, *args, **kwargs):
                pass

        return DnsZoneServiceStub(StubChannel())

    def wait_operation_and_get_result(self, *args, **kwargs):
        pass


@pytest.fixture()
def disable_sdk(monkeypatch):
    monkeypatch.setattr(yandexcloud, 'SDK', StubSDK)
    return None


@pytest.fixture()
def provider(disable_sdk):
    return YandexCloudProvider(
        "test", folder_id=STUB_FOLDER_ID, auth_type=AUTH_TYPE_METADATA
    )


@pytest.fixture()
def provider_with_zone(monkeypatch, provider):
    def _list(request):
        return ListDnsZonesResponse(
            next_page_token='', dns_zones=[STUB_ZONE_PUBLIC]
        )

    monkeypatch.setattr(provider.dns_service, 'List', _list)
    return provider


class TestYandexCloudProvider:
    class TestAuth:
        class ProcessMock:
            def __init__(self, check_error=False, stdout=None):
                self.check_error = check_error
                self._stdout = stdout

            def check_returncode(self):
                if self.check_error:
                    raise subprocess.CalledProcessError(
                        returncode=1, cmd='non_existent_file'
                    )

            @property
            def stdout(self):
                return self._stdout

            @property
            def returncode(self):
                return 1

        @staticmethod
        def _get_auth_kwargs(auth_type, **kwargs):
            return YandexCloudProvider.get_auth_kwargs(
                auth_type,
                **{
                    'oauth_token': None,
                    'iam_token': None,
                    'sa_key_file': None,
                    'sa_key': None,
                    **kwargs,
                }
            )

        def test_auth_oauth(self):
            auth_kwargs = self._get_auth_kwargs(
                AUTH_TYPE_OAUTH, oauth_token=STUB_TOKEN
            )
            assert auth_kwargs.keys() == {'token'}
            assert auth_kwargs['token'] == STUB_TOKEN

        def test_auth_iam(self):
            auth_kwargs = self._get_auth_kwargs(
                AUTH_TYPE_IAM, iam_token=STUB_TOKEN
            )
            assert auth_kwargs.keys() == {'iam_token'}
            assert auth_kwargs['iam_token'] == STUB_TOKEN

        def test_auth_metadata(self):
            auth_kwargs = self._get_auth_kwargs(AUTH_TYPE_METADATA)
            assert len(auth_kwargs) == 0

        def test_auth_service_account_key(self):
            # Auth using Service Account key, provided in file
            with tempfile.NamedTemporaryFile('w+') as fp:
                json.dump(STUB_SA_KEY, fp)
                fp.flush()
                auth_kwargs = self._get_auth_kwargs(
                    AUTH_TYPE_SA_KEY, sa_key_file=fp.name
                )
                assert auth_kwargs.keys() == {'service_account_key'}
                assert auth_kwargs['service_account_key'] == STUB_SA_KEY

            with pytest.raises(
                YandexCloudConfigException, match=r".*non_existent_file.*"
            ):
                self._get_auth_kwargs(
                    AUTH_TYPE_SA_KEY, sa_key_file='non_existent_file'
                )

            # Auth using Service Account key, provided in config
            auth_kwargs = self._get_auth_kwargs(
                AUTH_TYPE_SA_KEY, sa_key=STUB_SA_KEY
            )
            assert auth_kwargs.keys() == {'service_account_key'}
            assert auth_kwargs['service_account_key'] == STUB_SA_KEY

            # Wrong SA key format
            del STUB_SA_KEY['id']
            with pytest.raises(
                YandexCloudConfigException, match=r".*sa_key.*fields.*"
            ):
                self._get_auth_kwargs(AUTH_TYPE_SA_KEY, sa_key=STUB_SA_KEY)

        def test_auth_cli(self, monkeypatch):
            def _not_found(*args, **kwargs):
                raise FileNotFoundError()

            monkeypatch.setattr(
                subprocess,
                "run",
                lambda *args, **kwargs: self.ProcessMock(
                    stdout=STUB_TOKEN.encode('utf-8')
                ),
            )
            auth_kwargs = self._get_auth_kwargs(AUTH_TYPE_YC_CLI)
            assert auth_kwargs.keys() == {'token'}
            assert auth_kwargs['token'] == STUB_TOKEN
            monkeypatch.undo()

            monkeypatch.setattr(subprocess, "run", _not_found)
            with pytest.raises(YandexCloudConfigException):
                self._get_auth_kwargs(AUTH_TYPE_YC_CLI)
            monkeypatch.undo()

            monkeypatch.setattr(
                subprocess,
                "run",
                lambda *args, **kwargs: self.ProcessMock(check_error=True),
            )
            with pytest.raises(YandexCloudConfigException):
                self._get_auth_kwargs(AUTH_TYPE_YC_CLI)
            monkeypatch.undo()

            # Unknown auth type
            with pytest.raises(YandexCloudConfigException):
                self._get_auth_kwargs('non_existent_type')

    class TestFindZone:
        def test_find_zone_found_one(self, monkeypatch, provider):
            def _list(request):
                return ListDnsZonesResponse(
                    next_page_token='', dns_zones=[STUB_IDNA_ZONE]
                )

            monkeypatch.setattr(provider.dns_service, 'List', _list)
            zone_id = provider.get_zone_id_by_name(STUB_IDNA_ZONE_NAME)
            assert zone_id == STUB_IDNA_ZONE.id

        def test_find_zone_mapped(self, monkeypatch, disable_sdk):
            def _list(request):
                return ListDnsZonesResponse(
                    next_page_token='',
                    dns_zones=[STUB_ZONE_1, STUB_ZONE_2, STUB_ZONE_PUBLIC],
                )

            provider = YandexCloudProvider(
                "test",
                folder_id=STUB_FOLDER_ID,
                auth_type=AUTH_TYPE_METADATA,
                zone_ids_map={
                    STUB_ZONE_NAME: STUB_ZONE_2.id,
                    idna_decode(STUB_IDNA_ZONE_NAME): STUB_IDNA_ZONE.id,
                },
            )
            monkeypatch.setattr(provider.dns_service, 'List', _list)
            zone_id = provider.get_zone_id_by_name(STUB_ZONE_NAME)
            assert zone_id == STUB_ZONE_2.id

            def _list_idna(request):
                return ListDnsZonesResponse(
                    next_page_token='',
                    dns_zones=[STUB_ZONE_1, STUB_ZONE_2, STUB_IDNA_ZONE],
                )

            monkeypatch.setattr(provider.dns_service, 'List', _list_idna)
            zone_id = provider.get_zone_id_by_name(STUB_IDNA_ZONE_NAME)
            assert zone_id == STUB_IDNA_ZONE.id

        def test_find_zone_not_found(self, monkeypatch, provider):
            def _list(request):
                return ListDnsZonesResponse(next_page_token='', dns_zones=[])

            monkeypatch.setattr(provider.dns_service, 'List', _list)
            zone_id = provider.get_zone_id_by_name(STUB_ZONE_NAME)
            assert zone_id is None

        def test_find_zone_multiple_public(self, monkeypatch, disable_sdk):
            def _list(request):
                return ListDnsZonesResponse(
                    next_page_token='',
                    dns_zones=[STUB_ZONE_1, STUB_ZONE_PUBLIC, STUB_ZONE_2],
                )

            provider = YandexCloudProvider(
                "test",
                folder_id=STUB_FOLDER_ID,
                auth_type=AUTH_TYPE_METADATA,
                prioritize_public=True,
            )
            monkeypatch.setattr(provider.dns_service, 'List', _list)
            zone_id = provider.get_zone_id_by_name(STUB_ZONE_NAME)
            assert zone_id == STUB_ZONE_PUBLIC.id

            def _list_without_public(request):
                return ListDnsZonesResponse(
                    next_page_token='', dns_zones=[STUB_ZONE_1, STUB_ZONE_2]
                )

            monkeypatch.setattr(
                provider.dns_service, 'List', _list_without_public
            )
            zone_id = provider.get_zone_id_by_name(STUB_ZONE_NAME)
            assert zone_id == STUB_ZONE_1.id

        def test_find_zone_multiple_private(self, monkeypatch, disable_sdk):
            def _list(request):
                return ListDnsZonesResponse(
                    next_page_token='',
                    dns_zones=[STUB_ZONE_PUBLIC, STUB_ZONE_1, STUB_ZONE_2],
                )

            provider = YandexCloudProvider(
                "test",
                folder_id=STUB_FOLDER_ID,
                auth_type=AUTH_TYPE_METADATA,
                prioritize_public=False,
            )
            monkeypatch.setattr(provider.dns_service, 'List', _list)
            zone_id = provider.get_zone_id_by_name(STUB_ZONE_NAME)
            assert zone_id == STUB_ZONE_1.id

    class TestMapping:
        def test_mapping_supported(self):
            zone = Zone(STUB_ZONE_NAME, [])
            for type in YandexCloudProvider.SUPPORTS:
                rset = STUB_RECORDS[type.split('/')[-1]]
                # Make rset copy because of ANAME handling
                record = map_rset_to_octodns(
                    None, zone, False, rset.__deepcopy__()
                )

                recovered_rset = map_octodns_to_rset(record)
                assert rset.name == recovered_rset.name
                assert rset.type == recovered_rset.type
                assert rset.ttl == recovered_rset.ttl
                assert sorted(rset.data) == sorted(recovered_rset.data)

        def test_mapping_lenient(self):
            zone = Zone(STUB_ZONE_NAME, [])
            records = map(
                lambda x: STUB_RECORDS[x],
                (
                    'CAA_quoted',
                    'TXT_quoted',
                    'CNAME_nodot',
                    'CNAME_dot',
                    'MX_nodot',
                    'SRV_nodot',
                    'ANAME_nodot',
                ),
            )
            for rset in records:
                # Just check that it maps
                map_rset_to_octodns(None, zone, True, rset)

        def test_mapping_unknown(self):
            with pytest.raises(YandexCloudException):
                map_rset_to_octodns(
                    None,
                    None,
                    True,
                    RecordSet(
                        name="test.example.com.",
                        type="NON_EXISTENT_TYPE",
                        ttl=300,
                        data=["127.0.0.1", "127.0.0.2"],
                    ),
                )

    class TestPopulate:
        def test_populate_not_found(self, monkeypatch, provider):
            def _list(request):
                return ListDnsZonesResponse(next_page_token='', dns_zones=[])

            monkeypatch.setattr(provider.dns_service, 'List', _list)

            zone = Zone(STUB_ZONE_NAME, [])
            b = provider.populate(zone)
            assert not b
            assert len(zone.records) == 0

        def test_populate_single_page(self, monkeypatch, provider_with_zone):
            def _list_recordsets(request):
                return ListDnsZoneRecordSetsResponse(
                    next_page_token='',
                    record_sets=[STUB_RECORDS['A'], STUB_RECORDS['SOA']],
                )

            monkeypatch.setattr(
                provider_with_zone.dns_service,
                'ListRecordSets',
                _list_recordsets,
            )

            zone = Zone(STUB_ZONE_NAME, [])
            b = provider_with_zone.populate(zone)
            assert b
            assert (
                len(zone.records) == 1
            )  # SOA ignored because it is not on provider's (and octodns) SUPPORTS list

        def test_populate_multiple_pages(self, monkeypatch, provider_with_zone):
            TEST_RECORDS = list(STUB_RECORDS.values())

            def _list_recordsets(request):
                offset = int(request.page_token) if request.page_token else 0
                next_offset = offset + 10
                rsets = TEST_RECORDS[offset:next_offset]
                if next_offset >= len(TEST_RECORDS):
                    next_offset = ''
                return ListDnsZoneRecordSetsResponse(
                    next_page_token=str(next_offset), record_sets=rsets
                )

            monkeypatch.setattr(
                provider_with_zone.dns_service,
                'ListRecordSets',
                _list_recordsets,
            )

            zone = Zone(STUB_ZONE_NAME, [])
            b = provider_with_zone.populate(zone, lenient=True)
            assert b
            assert len(zone.records) == len(STUB_RECORDS) - 1  # without SOA

    class TestApply:
        @staticmethod
        def _make_plan(create, delete, update):
            zone = Zone(STUB_ZONE_NAME, [])
            return Plan(
                existing=None,
                desired=zone,
                changes=[
                    *map(
                        lambda x: Create(
                            map_rset_to_octodns(None, zone, True, x)
                        ),
                        create,
                    ),
                    *map(
                        lambda x: Delete(
                            map_rset_to_octodns(None, zone, True, x)
                        ),
                        delete,
                    ),
                    *map(
                        lambda x: Update(
                            map_rset_to_octodns(None, zone, True, x[0]),
                            map_rset_to_octodns(None, zone, True, x[1]),
                        ),
                        update,
                    ),
                ],
                exists=False,
            )

        @staticmethod
        def _compare_rset_batches(result, expected):
            result_str = sorted(map(lambda x: x.SerializeToString(), result))
            expected_str = sorted(
                map(lambda x: x.SerializeToString(), expected)
            )
            assert result_str == expected_str

        def test_apply_not_found(self, monkeypatch, provider):
            def _list(request):
                return ListDnsZonesResponse(next_page_token='', dns_zones=[])

            monkeypatch.setattr(provider.dns_service, 'List', _list)

            with pytest.raises(YandexCloudException):
                provider.apply(self._make_plan([], [], []))

        def test_apply_simple(self, monkeypatch, provider_with_zone):
            additions, deletions = [], []

            def _update_record_sets(request):
                additions.append(list(request.additions))
                deletions.append(list(request.deletions))
                return None

            monkeypatch.setattr(
                provider_with_zone.dns_service,
                'UpdateRecordSets',
                _update_record_sets,
            )

            # Large UPDATE_CHUNK_SIZE will put update in the same operation as delete & create
            provider_with_zone.apply(
                self._make_plan(
                    delete=[STUB_RECORDS['A']],
                    create=[STUB_RECORDS['MX']],
                    update=[
                        (STUB_RECORDS['CNAME_nodot'], STUB_RECORDS['CNAME'])
                    ],
                )
            )
            assert len(additions) == 1
            assert len(deletions) == 1

            self._compare_rset_batches(
                deletions[0], [STUB_RECORDS['A'], STUB_RECORDS['CNAME_nodot']]
            )
            self._compare_rset_batches(
                additions[0], [STUB_RECORDS['MX'], STUB_RECORDS['CNAME']]
            )

        def test_apply_big(self, monkeypatch, provider_with_zone):
            additions, deletions = [], []

            def _update_record_sets(request):
                additions.append(list(request.additions))
                deletions.append(list(request.deletions))
                return None

            provider_with_zone.UPDATE_CHUNK_SIZE = 2
            monkeypatch.setattr(
                provider_with_zone.dns_service,
                'UpdateRecordSets',
                _update_record_sets,
            )

            # Small UPDATE_CHUNK_SIZE will put update in different operation
            batch1_delete = [STUB_RECORDS['A'], STUB_RECORDS['CAA']]
            batch1_create = [STUB_RECORDS['AAAA'], STUB_RECORDS['CNAME']]
            batch2_delete = []
            batch2_create = [STUB_RECORDS['NS']]
            batch3_delete = [
                STUB_RECORDS['PTR_nodot'],
                STUB_RECORDS['SRV_nodot'],
            ]
            batch3_create = [STUB_RECORDS['PTR'], STUB_RECORDS['SRV']]

            provider_with_zone.apply(
                self._make_plan(
                    delete=batch1_delete + batch2_delete,
                    create=batch1_create + batch2_create,
                    update=[
                        (batch3_delete[0], batch3_create[0]),
                        (batch3_delete[1], batch3_create[1]),
                    ],
                )
            )
            assert len(additions) == 3
            assert len(deletions) == 3

            self._compare_rset_batches(deletions[0], batch1_delete)
            self._compare_rset_batches(additions[0], batch1_create)

            self._compare_rset_batches(deletions[1], batch2_delete)
            self._compare_rset_batches(additions[1], batch2_create)

            self._compare_rset_batches(deletions[2], batch3_delete)
            self._compare_rset_batches(additions[2], batch3_create)

        def test_apply_error(self, monkeypatch, provider_with_zone):
            def _update_record_sets(request):
                class RPCStateMock:
                    code = 1
                    details = "Some error"

                raise grpc.RpcError(RPCStateMock())

            monkeypatch.setattr(
                provider_with_zone.dns_service,
                'UpdateRecordSets',
                _update_record_sets,
            )

            with pytest.raises(YandexCloudException):
                provider_with_zone.apply(
                    self._make_plan([STUB_RECORDS['A']], [], [])
                )
