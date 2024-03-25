import functools

import pytest

from octodns.provider.plan import Plan
from octodns.record import Create, Delete, PtrRecord, Update
from octodns.zone import Zone

from octodns_yandex import Yandex360Provider
from octodns_yandex.yandex360_provider import (
    Yandex360ApiException,
    Yandex360Exception,
    map_entries_to_records,
    map_record_to_entries,
)
from tests.fixtures.ya360 import (
    STUB_DOMAIN_1,
    STUB_DOMAIN_2,
    STUB_ENTRIES,
    STUB_ORG_1,
    STUB_ORG_2,
    make_cursor_resp,
    make_paginated_resp,
)


@pytest.fixture()
def provider(monkeypatch):
    return Yandex360Provider('test', 'token')


class TestYandex360Provider:
    def test_make_request(self, provider, monkeypatch):
        class MockSession:
            status_code = 200
            text = "Test body"

            @staticmethod
            def request(*args, **kwargs):
                return MockSession

            @staticmethod
            def json():
                return {}

        monkeypatch.setattr(provider, "_session", MockSession)

        provider.make_request('GET', '/test', expected_code=200)
        with pytest.raises(
            Yandex360ApiException, match=f".*{MockSession.text}.*"
        ):
            provider.make_request('GET', '/test', expected_code=204)

    def test_api_urls(self, provider, monkeypatch):
        last_method, last_url = None, None

        def save_args(method, url, *args, **kwargs):
            nonlocal last_method, last_url
            last_method = method
            last_url = url

        monkeypatch.setattr(provider, 'make_request', save_args)

        provider.list_orgs(page_token=None)
        assert (last_method, last_url) == ('GET', '/directory/v1/org')

        provider.list_domains(123, page=1)
        assert (last_method, last_url) == (
            'GET',
            "/directory/v1/org/123/domains",
        )

        provider.list_dns_records(123, 'example.com')
        assert (last_method, last_url) == (
            'GET',
            '/directory/v1/org/123/domains/example.com/dns',
        )

        provider.create_dns_record(123, 'example.com', {})
        assert (last_method, last_url) == (
            'POST',
            '/directory/v1/org/123/domains/example.com/dns',
        )

        provider.update_dns_record(123, 'example.com', 12345, {})
        assert (last_method, last_url) == (
            'POST',
            '/directory/v1/org/123/domains/example.com/dns/12345',
        )

        provider.delete_dns_record(123, 'example.com', 12345)
        assert (last_method, last_url) == (
            'DELETE',
            '/directory/v1/org/123/domains/example.com/dns/12345',
        )

    def test_find_org_not_found(self, provider, monkeypatch):
        monkeypatch.setattr(
            provider,
            'list_orgs',
            lambda page_token: make_cursor_resp('', organizations=[]),
        )

        found_org_id = provider.find_org_id_for_domain(STUB_DOMAIN_1['name'])
        assert found_org_id is None

    def test_find_org_multiple_pages(self, provider, monkeypatch):
        def _list_orgs(page_token):
            if not page_token:
                orgs = [STUB_ORG_1]
            else:
                orgs = [STUB_ORG_2]
            return make_cursor_resp(
                '2' if not page_token else '', organizations=orgs
            )

        def _list_domains(org_id, page):
            if org_id == STUB_ORG_1['id']:
                domains = []
            elif page == 1:
                domains = [STUB_DOMAIN_1]
            else:
                domains = [STUB_DOMAIN_2]
            return make_paginated_resp(page, 2, 1, 2, domains=domains)

        monkeypatch.setattr(provider, 'list_orgs', _list_orgs)
        monkeypatch.setattr(provider, 'list_domains', _list_domains)

        found_org_id = provider.find_org_id_for_domain(STUB_DOMAIN_2['name'])
        assert found_org_id == STUB_ORG_2['id']

    def test_mapping_supported(self):
        zone = Zone('example.com.', [])

        for type in Yandex360Provider.SUPPORTS:
            entries = STUB_ENTRIES[type.split('/')[-1]]
            records = map_entries_to_records(None, zone, False, entries)
            assert len(records) == 1

            ttls = set(map(lambda x: x['ttl'], entries))

            recovered_entries = map_record_to_entries(zone, records[0])
            assert len(recovered_entries) == len(entries)

            for i in range(len(recovered_entries)):
                copy = entries[i].copy()
                del copy['recordId'], copy['ttl']
                ttl = recovered_entries[i].pop('ttl')

                assert recovered_entries[i] == copy
                assert ttl in ttls

    def test_mapping_unknown(self):
        zone = Zone('example.com.', [])

        # Not known to octodns
        with pytest.raises(Yandex360Exception):
            map_entries_to_records(
                None,
                zone,
                False,
                [
                    {
                        'recordId': 8,
                        'type': 'NON_EXISTENT_TYPE',
                        'name': '@',
                        'ttl': 600,
                    }
                ],
            )

        # Not known to yandex 360
        with pytest.raises(Yandex360Exception):
            map_entries_to_records(
                None,
                zone,
                False,
                [{'recordId': 8, 'type': 'PTR', 'name': '@', 'ttl': 600}],
            )

        with pytest.raises(Yandex360Exception):
            map_record_to_entries(
                zone,
                PtrRecord(zone, "test", {'ttl': 600, 'value': "example.com."}),
            )

    def test_collect_zone_entries(self, provider, monkeypatch):
        def _list_dns_records(org_id, domain_name, page):
            if page == 1:
                records = STUB_ENTRIES['A']
            else:
                records = STUB_ENTRIES['MX']
            return make_paginated_resp(page, 2, 1, 2, records=records)

        monkeypatch.setattr(provider, 'list_dns_records', _list_dns_records)

        entries = provider.collect_zone_entries(
            STUB_ORG_1['id'], STUB_DOMAIN_1['name']
        )
        assert entries == STUB_ENTRIES['A'] + STUB_ENTRIES['MX']

    def test_populate_not_found(self, provider, monkeypatch):
        zone = Zone('example.com.', [])

        monkeypatch.setattr(
            provider, 'find_org_id_for_domain', lambda domain_name: None
        )

        result = provider.populate(zone)
        assert not result

    def test_populate_found(self, provider, monkeypatch):
        TEST_ENTRIES = list(
            functools.reduce(lambda acc, x: acc + x, STUB_ENTRIES.values(), [])
        )
        zone = Zone('example.com.', [])

        monkeypatch.setattr(
            provider,
            'find_org_id_for_domain',
            lambda domain_name: STUB_ORG_1['id'],
        )
        monkeypatch.setattr(
            provider,
            'collect_zone_entries',
            lambda org_id, domain_name: TEST_ENTRIES,
        )

        result = provider.populate(zone, lenient=True)
        assert result

        assert len(zone.records) == len(STUB_ENTRIES.keys())

    @staticmethod
    def _make_plan(create, delete, update):
        zone = Zone('example.com.', [])
        return Plan(
            existing=None,
            desired=zone,
            changes=[
                *map(Create, map_entries_to_records(None, zone, True, create)),
                *map(Delete, map_entries_to_records(None, zone, True, delete)),
                *map(
                    lambda x: Update(*x),
                    map(
                        lambda x: (
                            map_entries_to_records(None, zone, True, x[0])[0],
                            map_entries_to_records(None, zone, True, x[1])[0],
                        ),
                        update,
                    ),
                ),
            ],
            exists=False,
        )

    def test_apply_not_found(self, provider, monkeypatch):
        monkeypatch.setattr(
            provider, 'find_org_id_for_domain', lambda domain_name: None
        )
        with pytest.raises(Yandex360Exception):
            provider.apply(self._make_plan([], [], []))

    def test_apply(self, provider, monkeypatch):
        TEST_ENTRIES = functools.reduce(
            lambda acc, x: acc + x, STUB_ENTRIES.values(), []
        )
        created_tuples, deleted_ids, updated_ids = [], [], []

        monkeypatch.setattr(
            provider,
            'find_org_id_for_domain',
            lambda domain_name: STUB_ORG_1['id'],
        )
        monkeypatch.setattr(
            provider,
            'collect_zone_entries',
            lambda org_id, domain_name: TEST_ENTRIES,
        )

        monkeypatch.setattr(
            provider,
            'delete_dns_record',
            lambda org_id, domain, record_id: deleted_ids.append(record_id),
        )
        monkeypatch.setattr(
            provider,
            'create_dns_record',
            lambda org_id, domain, data: created_tuples.append(
                (data['type'], data['name'])
            ),
        )
        monkeypatch.setattr(
            provider,
            'update_dns_record',
            lambda org_id, domain, record_id, data: updated_ids.append(
                record_id
            ),
        )

        provider.apply(
            self._make_plan(
                create=STUB_ENTRIES['A'] + STUB_ENTRIES['CNAME'],
                delete=STUB_ENTRIES['MX'] + STUB_ENTRIES['SRV'],
                update=[
                    (
                        STUB_ENTRIES['CNAME'],
                        STUB_ENTRIES['CNAME_mail'],
                    ),  # Basic update
                    (
                        STUB_ENTRIES['A'],
                        STUB_ENTRIES['A_single'],
                    ),  # Remove one entry
                    (
                        STUB_ENTRIES['AAAA'],
                        STUB_ENTRIES['AAAA_triple'],
                    ),  # Add one entry
                    # CAA update is broken, so just make sure it does not invoke an update operation
                    (STUB_ENTRIES['CAA'], STUB_ENTRIES['CAA']),
                ],
            )
        )

        # Check applied operations
        # NOTE: octodns could reorder changes before applying
        assert created_tuples == list(
            map(
                lambda x: (x['type'], x['name']),
                STUB_ENTRIES['A']
                + STUB_ENTRIES['CNAME']
                + STUB_ENTRIES['CAA']
                + [STUB_ENTRIES['AAAA_triple'][2]],
            )
        )
        assert deleted_ids == list(
            map(
                lambda x: x['recordId'],
                STUB_ENTRIES['MX']
                + STUB_ENTRIES['SRV']
                + STUB_ENTRIES['CAA']
                + [STUB_ENTRIES['A'][1]],
            )
        )
        assert updated_ids == list(
            map(
                lambda x: x['recordId'],
                [STUB_ENTRIES['A'][0]]
                + STUB_ENTRIES['AAAA']
                + STUB_ENTRIES['CNAME'],
            )
        )
