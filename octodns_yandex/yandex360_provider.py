import itertools
from collections import defaultdict
from logging import getLogger

import requests
from octodns import __VERSION__ as octodns_version
from octodns.idna import idna_encode
from octodns.provider.base import BaseProvider
from octodns.record import Record

from octodns_yandex.version import __VERSION__ as provider_version


def map_entries_to_records(provider, zone, lenient, entries):
    def _keyfunc(x):
        return x['name'], x['type'],

    records = []
    entries = sorted(entries, key=_keyfunc)
    for k, entry_group in itertools.groupby(entries, _keyfunc):
        name, type = k
        entry_group = list(entry_group)
        record_type = Record.registered_types().get(type, None)

        if record_type is None:
            raise Exception(f"Unknown record type: {type}")

        data = {
            'type': type,
            'ttl': entry_group[0]['ttl'],  # We don't really can determine TTL
        }

        value_type = record_type._value_type
        values = []
        for entry in entry_group:
            if type in {'A', 'AAAA', }:
                values.append(value_type(entry['address']))
            elif type in {'CNAME', 'NS', }:
                values.append(value_type(entry['target']))
            elif type == 'TXT':
                # Hard escape to meet octodns requirements. We will unescape on apply
                values.append(value_type(entry['text'].replace(';', '\\;')))
            elif type == 'MX':
                values.append(
                    value_type({
                        'preference': int(entry['preference']),
                        'exchange': entry['exchange'],
                    })
                )
            elif type == 'SRV':
                values.append(
                    value_type({
                        'priority': int(entry['priority']),
                        'weight': int(entry['weight']),
                        'port': int(entry['port']),
                        'target': entry['target'],
                    })
                )
            elif type == 'CAA':
                values.append(
                    value_type({
                        'flags': int(entry['flag']),
                        'tag': entry['tag'],
                        'value': entry['value'],
                    })
                )
        if len(values) == 1:
            data['value'] = values[0]
        else:
            data['values'] = values

        records.append(
            Record.new(
                zone,
                name if name != '@' else '',
                data=data,
                source=provider,
                lenient=lenient
            )
        )

    return records


def map_record_to_entries(zone, record: Record):
    type = record._type
    name = zone.hostname_from_fqdn(record.name)
    base_data = {
        'name': name if name else '@',
        'type': type,
        'ttl': int(record.ttl),
    }
    entries = []

    values = record.data.get('values', record.data.get('value', []))
    values = values if isinstance(values, (list, tuple)) else [values]
    for value in values:
        if type in {'A', 'AAAA', }:
            entries.append({**base_data, 'address': value})
        elif type in {'CNAME', 'NS', }:
            entries.append({**base_data, 'target': value})
        elif type == 'TXT':
            # NOTE: Yandex 360 is escaping semicolons properly
            # XXX: Yandex 360 is doubling backslashes
            entries.append({**base_data, 'text': value.replace('\\;', ';').replace('\\\\', '\\')})
        elif type == 'MX':
            entries.append({
                **base_data,
                'preference': int(value.preference),
                'exchange': value.exchange,
            })
        elif type == 'SRV':
            entries.append({
                **base_data,
                'priority': int(value.priority),
                'weight': int(value.weight),
                'port': int(value.port),
                'target': value.target,
            })
        elif type == 'CAA':  # no update?
            entries.append({
                **base_data,
                'flag': int(value.flags),
                'tag': value.tag,
                'value': value.value,  # wrap with ""?
            })
        else:
            raise Exception()
    return entries


class Yandex360Provider(BaseProvider):
    SUPPORTS_GEO = False
    SUPPORTS_DYNAMIC = False
    SUPPORTS = str({
        'A',
        'AAAA',
        'CNAME',
        'MX',
        'TXT',
        'SRV',
        'NS',
        'CAA',
    })

    TIMEOUT = 15
    API_BASE = 'https://api360.yandex.net'

    _oauth_token = None

    def __init__(
        self,
        id,
        oauth_token,

        *args,
        **kwargs
    ):
        self.log = getLogger(f"Yandex360Provider[{id}]")

        self._oauth_token = oauth_token

        self.log.debug('__init__: oauth_token=%s', self._oauth_token)

        super().__init__(id, *args, **kwargs)

        self._session = requests.Session()
        self._session.headers.update({
            'Authorization': f"OAuth {self._oauth_token}",
            'User-Agent': f"octodns/{octodns_version} octodns-yandex/{provider_version}",
        })

    def make_request(self, method, url, data=None, params=None, expected_code=200):
        resp = self._session.request(method, f"{self.API_BASE}{url}", params=params, json=data, timeout=self.TIMEOUT)
        if resp.status_code != expected_code:
            raise Exception()
        return resp.json()

    def list_orgs(self, page_token=None):
        return self.make_request('GET', '/directory/v1/org', params={
            'pageSize': 100,
            'pageToken': page_token
        })

    def list_domains(self, org_id, page=1):
        return self.make_request('GET', f"/directory/v1/org/{org_id}/domains", params={
            'perPage': 10,
            'page': page
        })

    def list_dns_records(self, org_id, domain, page=1):
        return self.make_request('GET', f"/directory/v1/org/{org_id}/domains/{domain}/dns", params={
            'perPage': 50,
            'page': page
        })

    def create_dns_record(self, org_id, domain, data):
        self.log.debug("API Create org_id=%s, domain=%s, data=%s", org_id, domain, data)
        return self.make_request('POST', f"/directory/v1/org/{org_id}/domains/{domain}/dns", data=data)

    def update_dns_record(self, org_id, domain, record_id, data):
        self.log.debug("API Update org_id=%s, domain=%s, record_id+%s, data=%s", org_id, domain, record_id, data)
        return self.make_request('POST', f"/directory/v1/org/{org_id}/domains/{domain}/dns/{record_id}", data=data)

    def delete_dns_record(self, org_id, domain, record_id):
        self.log.debug("API Delete org_id=%s, domain=%s, record_id=%s", org_id, domain, record_id)
        return self.make_request('DELETE', f"/directory/v1/org/{org_id}/domains/{domain}/dns/{record_id}")

    def find_org_id_for_domain(self, domain_name):
        orgs_done = False
        orgs_page_token = None
        while not orgs_done:
            orgs_resp = self.list_orgs(page_token=orgs_page_token)

            if orgs_resp['nextPageToken']:
                orgs_page_token = orgs_resp['nextPageToken']
            else:
                orgs_done = True

            for org in orgs_resp['organizations']:
                org_id = org['id']

                domains_page, domains_pages = 1, 1
                while domains_page <= domains_pages:
                    domains_resp = self.list_domains(org_id, page=domains_page)

                    domains_pages = domains_resp['pages']
                    domains_page += 1

                    for domain in domains_resp['domains']:
                        if domain['name'] != domain_name:
                            continue
                        self.log.info('find_org_id_for_domain: Found org_id=%s for domain_name=%s', org_id, domain_name)
                        return org_id

        return None

    def collect_zone_entries(self, org_id, domain_name):
        entries = []

        records_page, records_pages = 1, 1
        while records_page <= records_pages:
            domains_resp = self.list_dns_records(org_id, domain_name, page=records_page)

            records_pages = domains_resp['pages']
            records_page += 1

            entries += domains_resp['records']

        return entries

    def populate(self, zone, target=False, lenient=False):
        self.log.debug(
            'populate: name=%s, target=%s, lenient=%s',
            zone.name,
            target,
            lenient,
        )

        domain_name = idna_encode(zone.name).rstrip('.')
        org_id = self.find_org_id_for_domain(domain_name)
        if org_id is None:
            self.log.info('populate: Zone not found')
            return False

        before = len(zone.records)
        entries = self.collect_zone_entries(org_id, domain_name)
        for record in map_entries_to_records(self, zone, lenient, entries):
            zone.add_record(record, lenient=lenient)

        self.log.info('populate: found %s records', len(zone.records) - before)

        return True

    def _apply(self, plan):
        zone = plan.desired
        changes = plan.changes

        domain_name = idna_encode(zone.name).rstrip('.')
        org_id = self.find_org_id_for_domain(domain_name)
        if org_id is None:
            raise Exception("Zone not found")

        self.log.debug(
            '_apply: org_id=%s, domain_name=%s, len(changes)=%d', org_id, domain_name, len(changes)
        )

        delete, create, update = [], [], []
        records_to_search = defaultdict(dict)
        for change in changes:
            if change.existing is None:
                create.append(change)
            else:
                records_to_search[change.existing._type][zone.hostname_from_fqdn(change.existing.name)] = []
                if change.new is None:
                    delete.append(change)
                else:
                    update.append(change)

        # Search for record_ids by (type, name) tuples
        entries = self.collect_zone_entries(org_id, domain_name)
        for entry in entries:
            e = records_to_search[entry['type']].get(entry['name'], None)
            if e is None:
                continue
            records_to_search[entry['type']][entry['name']].append(entry['recordId'])

        # Delete found records
        for change in delete:
            for record_id in records_to_search[change.existing._type][zone.hostname_from_fqdn(change.existing.name)]:
                self.delete_dns_record(org_id, domain_name, record_id)

        # Create new records
        for change in create:
            for entry in map_record_to_entries(zone, change.new):
                self.create_dns_record(org_id, domain_name, entry)

        # Apply changes: update (if possible) or create/delete
        for change in update:
            it = iter(records_to_search[change.existing._type][zone.hostname_from_fqdn(change.existing.name)])

            # Update entries while there is some or create new ones
            for entry in map_record_to_entries(zone, change.new):
                record_id = next(it, None)
                if record_id is not None:
                    self.update_dns_record(org_id, domain_name, record_id, entry)
                else:
                    self.create_dns_record(org_id, domain_name, entry)

            # Delete additional entries (if any)
            for record_id in it:
                self.delete_dns_record(org_id, domain_name, record_id)
