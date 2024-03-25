import json
import subprocess
from logging import getLogger

import grpc
import yandexcloud
from yandex.cloud.dns.v1.dns_zone_pb2 import RecordSet
from yandex.cloud.dns.v1.dns_zone_service_pb2 import (
    ListDnsZoneRecordSetsRequest,
    ListDnsZonesRequest,
    RecordSetDiff,
    UpdateRecordSetsMetadata,
    UpdateRecordSetsRequest,
)
from yandex.cloud.dns.v1.dns_zone_service_pb2_grpc import DnsZoneServiceStub

from octodns import __VERSION__ as octodns_version
from octodns.idna import idna_decode
from octodns.provider import ProviderException
from octodns.provider.base import BaseProvider
from octodns.record import Record

from octodns_yandex.record import YandexCloudAnameRecord
from octodns_yandex.version import __VERSION__ as provider_version


class YandexCloudException(ProviderException):
    pass


class YandexCloudConfigException(YandexCloudException):
    pass


def _aname_type_map(rset):
    rset.type = YandexCloudAnameRecord._type


def _txt_unescape(rset):
    # unescape value because octodns escaping breaks escaped dkim
    for i, value in enumerate(rset.data):
        rset.data[i] = value.replace('\\;', ';')


rset_transformers = {
    # Custom transformers for RecordSets from API
    'ANAME': _aname_type_map,
    'TXT': _txt_unescape,
}


def map_rset_to_octodns(provider, zone, lenient, rset):
    rset_transformers.get(rset.type, lambda *args: None)(rset)

    record_type = Record.registered_types().get(rset.type, None)
    if record_type is None:
        raise YandexCloudException(f"Unknown record type: {rset.type}")

    data = {'type': record_type._type, 'ttl': rset.ttl}

    values = record_type.parse_rdata_texts(rset.data)
    if len(values) == 1:
        data['value'] = values[0]
    else:
        data['values'] = values

    # name = zone.hostname_from_fqdn(rset.name)
    # fqdn = rset.name
    # if 0 < len(record_type.validate(name, fqdn, data)):
    #     data['octodns'] = {'lenient': True}

    return Record.new(
        zone,
        zone.hostname_from_fqdn(rset.name),
        data=data,
        source=provider,
        lenient=lenient,
    )


def map_octodns_to_rset(record: Record):
    values = record.data.get('values', record.data.get('value', []))
    values = values if isinstance(values, (list, tuple)) else [values]

    return RecordSet(
        name=record.fqdn,
        type=record._type.split('/')[-1],  # handle custom records
        ttl=record.ttl,
        data=[e.rdata_text for e in values],
    )


AUTH_TYPE_OAUTH = 'oauth'
AUTH_TYPE_IAM = 'iam'
AUTH_TYPE_METADATA = 'metadata'
AUTH_TYPE_SA_KEY = 'sa-key'
AUTH_TYPE_YC_CLI = 'yc-cli'


class YandexCloudProvider(BaseProvider):
    SUPPORTS_GEO = False
    SUPPORTS_DYNAMIC = False
    SUPPORTS_MULTIVALUE_PTR = True
    SUPPORTS_ROOT_NS = True  # Useless?
    SUPPORTS = {
        'A',
        'AAAA',
        'CAA',
        'CNAME',
        'MX',
        'NS',
        'PTR',
        # 'SOA',
        'SRV',
        # 'SVCB',
        # 'HTTPS',
        'TXT',
        YandexCloudAnameRecord._type,
    }

    UPDATE_CHUNK_SIZE = 1000

    prioritize_public = None
    auth_kwargs = dict()
    zone_ids_map = dict()

    sdk = None
    dns_service = None

    def __init__(
        self,
        id: str,
        folder_id: str,
        auth_type: str,
        prioritize_public=None,
        zone_ids_map=None,
        oauth_token=None,
        iam_token=None,
        sa_key_file=None,
        sa_key=None,
        *args,
        **kwargs,
    ):
        self.log = getLogger(f"YandexCloudProvider[{id}]")

        self.folder_id = folder_id
        self.prioritize_public = prioritize_public

        if isinstance(zone_ids_map, dict):
            self.zone_ids_map = zone_ids_map

        self.auth_kwargs = self.get_auth_kwargs(
            auth_type, oauth_token, iam_token, sa_key_file, sa_key
        )
        self.log.debug(
            '__init__: folder_id=%s auth_type=%s auth_kwargs=%s',
            self.folder_id,
            auth_type,
            self.auth_kwargs,
        )

        super().__init__(id, *args, **kwargs)

        self.sdk = yandexcloud.SDK(
            user_agent=f"octodns/{octodns_version} octodns-yandex/{provider_version}",
            **self.auth_kwargs,
        )
        self.dns_service = self.sdk.client(DnsZoneServiceStub)

    @staticmethod
    def get_auth_kwargs(auth_type, oauth_token, iam_token, sa_key_file, sa_key):
        if auth_type == AUTH_TYPE_OAUTH:
            return {'token': oauth_token}
        elif auth_type == AUTH_TYPE_IAM:
            return {'iam_token': iam_token}
        elif auth_type == AUTH_TYPE_METADATA:
            return {}  # Auto configured by SDK
        elif auth_type == AUTH_TYPE_SA_KEY:
            if sa_key_file:
                try:
                    with open(sa_key_file) as infile:
                        sa_key = json.load(infile)
                except OSError as e:
                    raise YandexCloudConfigException(
                        f"Failed to open 'sa_key_file': {sa_key_file}"
                    ) from e
            if (
                sa_key is None
                or 'id' not in sa_key
                or 'service_account_id' not in sa_key
                or 'private_key' not in sa_key
            ):
                raise YandexCloudConfigException(
                    "Provider option 'sa_key' should be dict with fields: id, service_account_id, private_key"
                )
            return {'service_account_key': sa_key}
        elif auth_type == AUTH_TYPE_YC_CLI:
            process = None
            try:
                process = subprocess.run(
                    ['yc', 'config', 'get', 'token'], stdout=subprocess.PIPE
                )
                process.check_returncode()
            except FileNotFoundError as e:
                raise YandexCloudConfigException(
                    'yc binary not found in PATH'
                ) from e
            except subprocess.CalledProcessError as e:
                raise YandexCloudConfigException(
                    f"Failed to get token from yc, exit code: {process.returncode}"
                ) from e

            return {'token': process.stdout.decode('utf-8').strip()}
        else:
            raise YandexCloudConfigException("Unknown auth type")

    def get_zone_id_by_name(self, zone_name):
        decoded_name = idna_decode(zone_name)
        mapped_id = self.zone_ids_map.get(
            decoded_name, self.zone_ids_map.get(zone_name, None)
        )
        if mapped_id is not None:
            self.log.debug(
                'get_zone_id_by_name: Found zone_name=%s in zone_ids_map',
                zone_name,
            )
            return mapped_id

        self.log.debug('get_zone_id_by_name: name=%s', decoded_name)

        # XXX: Will miss public zone if there is more than 1000 equally named internal zones
        zones = self.dns_service.List(
            ListDnsZonesRequest(
                folder_id=self.folder_id, filter=f'zone="{zone_name}"'
            )
        ).dns_zones

        if len(zones) < 1:
            self.log.debug('get_zone_id_by_name: No zones found')
            return None

        if len(zones) > 1 and self.prioritize_public is not None:
            if self.prioritize_public:
                public_zone = [
                    e for e in zones if e.HasField('public_visibility')
                ]
                if len(public_zone) > 0:
                    zones = public_zone
                    self.log.info(
                        'get_zone_id_by_name: Using public zone for zone_name=%s',
                        zone_name,
                    )
            else:
                zones = [e for e in zones if e.HasField('private_visibility')]
                self.log.info(
                    'get_zone_id_by_name: Searching for internal zones: zone_name=%s',
                    zone_name,
                )

        if len(zones) > 1:
            self.log.warning(
                "get_zone_id_by_name: Multiple zones found for zone_name=%s.\n"
                "Use 'prioritize_public' provider option to use public zones when present.\n"
                "Or use 'zone_ids_map' provider option to specify exact zone ids",
                zone_name,
            )

        zone = zones[0]
        self.log.info(
            'get_zone_id_by_name: Found zone_id=%s for zone_name=%s',
            zone.id,
            zone_name,
        )
        return zone.id

    def populate(self, zone, target=False, lenient=False):
        self.log.debug(
            'populate: name=%s, target=%s, lenient=%s',
            zone.name,
            target,
            lenient,
        )

        zone_id = self.get_zone_id_by_name(zone.name)
        if zone_id is None:
            self.log.info('populate: Zone not found')
            return False

        before = len(zone.records)
        done = False
        page_token = None
        while not done:
            resp = self.dns_service.ListRecordSets(
                ListDnsZoneRecordSetsRequest(
                    dns_zone_id=zone_id, page_token=page_token
                )
            )

            if resp.next_page_token:
                page_token = resp.next_page_token
            else:
                done = True

            for rset in resp.record_sets:
                if rset.type not in self.SUPPORTS | {'ANAME'}:
                    continue
                record = map_rset_to_octodns(self, zone, lenient, rset)
                zone.add_record(record, lenient=lenient)

        self.log.info('populate: found %s records', len(zone.records) - before)
        return True

    def _apply_rset_update(self, zone_id, create, delete):
        self.log.debug(
            'Applying changes:\n- Create: %s\n- Delete: %s', create, delete
        )

        try:
            operation = self.dns_service.UpdateRecordSets(
                UpdateRecordSetsRequest(
                    dns_zone_id=zone_id,
                    additions=[map_octodns_to_rset(e.new) for e in create],
                    deletions=[map_octodns_to_rset(e.existing) for e in delete],
                )
            )
            self.sdk.wait_operation_and_get_result(
                operation,
                response_type=RecordSetDiff,
                meta_type=UpdateRecordSetsMetadata,
            )
        except grpc.RpcError as e:
            state = e.args[0]
            raise YandexCloudException(
                f"API error: code={state.code}, details={state.details}"
            ) from e

    def _apply(self, plan):
        zone_name = plan.desired.name
        changes = plan.changes

        zone_id = self.get_zone_id_by_name(zone_name)
        if zone_id is None:
            raise YandexCloudException(
                'Zone not found (zone creation is not supported)'
            )

        self.log.debug(
            '_apply: zone_id=%s, zone_name=%s, len(changes)=%d',
            zone_id,
            zone_name,
            len(changes),
        )

        delete, create, update = [], [], []
        for change in changes:
            if change.new is None:
                delete.append(change)
            elif change.existing is None:
                create.append(change)
            else:
                update.append(change)

        # Try to process create & delete operations simultaneous in batches
        # Also, if there is enough free space in batch for all updates, then add them
        for i in range(
            0, max(len(delete), len(create)), self.UPDATE_CHUNK_SIZE
        ):
            create_chunk = create[i : i + self.UPDATE_CHUNK_SIZE]
            delete_chunk = delete[i : i + self.UPDATE_CHUNK_SIZE]

            max_len = max(len(create_chunk), len(delete_chunk))
            if (
                max_len < self.UPDATE_CHUNK_SIZE
                and max_len + len(update) <= self.UPDATE_CHUNK_SIZE
            ):
                create_chunk += update
                delete_chunk += update
                update = []
            self._apply_rset_update(zone_id, create_chunk, delete_chunk)

        # Process updates separately (if it was not done before)
        # API guarantees that deletions processed before additions
        for i in range(0, len(update), self.UPDATE_CHUNK_SIZE):
            chunk = update[i : i + self.UPDATE_CHUNK_SIZE]

            self._apply_rset_update(zone_id, chunk, chunk)
