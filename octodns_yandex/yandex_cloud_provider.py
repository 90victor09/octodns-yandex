import subprocess
from logging import getLogger

from octodns import __VERSION__ as octodns_version
from octodns.idna import idna_encode
from octodns.provider.base import BaseProvider
from octodns.record import Record

from octodns_yandex.record import YandexCloudAnameRecord
from octodns_yandex.mappings import map_rset_to_octodns
from octodns_yandex.version import __VERSION__ as provider_version

import yandexcloud
from yandex.cloud.dns.v1.dns_zone_service_pb2_grpc import DnsZoneServiceStub
from yandex.cloud.dns.v1.dns_zone_service_pb2 import (
    ListDnsZonesRequest,
    ListDnsZoneRecordSetsRequest,
)

AUTH_TYPE_OAUTH = 'OAUTH'
AUTH_TYPE_METADATA = 'METADATA'
AUTH_TYPE_SA_KEY = 'SA_KEY'
AUTH_TYPE_IAM = 'IAM'
AUTH_TYPE_YC_CLI = 'YC_CLI'


class YandexCloudProvider(BaseProvider):
    SUPPORTS_GEO = False
    SUPPORTS_DYNAMIC = False
    SUPPORTS = str({
        'A',
        'AAAA',
        'CAA',
        'CNAME',
        # 'ANAME',
        'MX',
        'NS',
        'PTR',
        # 'SOA',
        'SRV',
        # 'SVCB',
        # 'HTTPS',
        'TXT',

        YandexCloudAnameRecord._type,
    })

    auth_kwargs = {}
    sdk = None
    dns_service = None

    def __init__(
        self,
        id,
        folder_id,
        auth_type=None,

        oauth_token=None,
        iam_token=None,

        sa_key_id=None,
        sa_key_account_id=None,
        sa_key_private_key=None,

        *args,
        **kwargs
    ):
        self.log = getLogger(f'YandexCloudProvider[{id}]')

        self.folder_id = folder_id

        self.resolve_auth(
            auth_type,

            oauth_token,
            iam_token,

            sa_key_id,
            sa_key_account_id,
            sa_key_private_key,
        )
        self.log.debug('__init__: folder_id=%s auth_type=%s auth_kwargs=%s', self.folder_id, auth_type, self.auth_kwargs)

        super().__init__(id, *args, **kwargs)

        self.sdk = yandexcloud.SDK(
            user_agent=f'octodns/{octodns_version} octodns-yandex/{provider_version}',
            **self.auth_kwargs
        )
        self.dns_service = self.sdk.client(DnsZoneServiceStub)

    def resolve_auth(
        self,
        auth_type,

        oauth_token,
        iam_token,

        sa_key_id,
        sa_key_account_id,
        sa_key_private_key,
    ):
        if auth_type == AUTH_TYPE_OAUTH:
            self.auth_kwargs['token'] = oauth_token
        elif auth_type == AUTH_TYPE_IAM:
            self.auth_kwargs['token'] = iam_token
        elif auth_type == AUTH_TYPE_SA_KEY:
            self.auth_kwargs['service_account_key'] = {
                'id': sa_key_id,
                'service_account_id': sa_key_account_id,
                'private_key': sa_key_private_key,
            }
        elif auth_type == AUTH_TYPE_METADATA:
            pass  # Auto configured
        elif auth_type == AUTH_TYPE_YC_CLI:
            try:
                process = subprocess.run(["yc", "config", "get", "token"], stdout=subprocess.PIPE)
                process.check_returncode()
            except FileNotFoundError:
                self.log.error("yc binary not found in PATH")
                raise Exception()
            except subprocess.CalledProcessError:
                self.log.error("Failed to get token from yc, exit code: %d", process.returncode)
                raise Exception()

            self.auth_kwargs['token'] = process.stdout.decode('utf-8').strip()

    def _get_zone_id_by_name(self, zone_name):
        zone_name = idna_encode(zone_name)
        self.log.debug("_get_zone_id_by_name: name=%s", zone_name)
        list_zones_resp = self.dns_service.List(ListDnsZonesRequest(
            folder_id=self.folder_id,
            # page_size=1,
            # page_token='',
            filter=f'zone="{zone_name}"'
        ))

        if len(list_zones_resp.dns_zones) < 1:
            return None

        return list_zones_resp.dns_zones[0].id

    def populate(self, zone, target=False, lenient=False):
        self.log.debug(
            'populate: name=%s, target=%s, lenient=%s',
            zone.name,
            target,
            lenient,
        )

        existing_zone_id = self._get_zone_id_by_name(zone.name)
        if existing_zone_id is None:
            self.log.info('populate: Zone not found')
            return False

        before = len(zone.records)
        done = False
        page_token = None
        while not done:
            resp = self.dns_service.ListRecordSets(ListDnsZoneRecordSetsRequest(
                dns_zone_id=existing_zone_id,
                page_token=page_token,
            ))

            if resp.next_page_token:
                page_token = resp.next_page_token
            else:
                done = True

            for rset in resp.record_sets:
                if rset.type not in self.SUPPORTS:
                    continue
                record = map_rset_to_octodns(self, zone, lenient, rset)
                zone.add_record(record, lenient=lenient)

        self.log.info('populate: found %s records', len(zone.records) - before)

        return True

    def _apply(self, plan):
        pass