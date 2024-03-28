from logging import getLogger

import yandexcloud
from yandex.cloud.cdn.v1.resource_service_pb2 import (
    GetProviderCNameRequest,
    ListResourcesRequest,
)
from yandex.cloud.cdn.v1.resource_service_pb2_grpc import ResourceServiceStub

from octodns.record import Record
from octodns.source.base import BaseSource

from octodns_yandex.auth import _AuthMixin
from octodns_yandex.version import get_user_agent


class YandexCloudCDNSource(_AuthMixin, BaseSource):
    SUPPORTS_GEO = False
    SUPPORTS = {'CNAME'}

    _provider_cname = None

    def __init__(
        self,
        id,
        folder_id: str,
        auth_type: str,
        record_ttl=3600,
        oauth_token=None,
        iam_token=None,
        sa_key_file=None,
        sa_key=None,
        *args,
        **kwargs,
    ):
        self.log = getLogger(f"YandexCloudCDNSource[{id}]")

        self.folder_id = folder_id
        self.record_ttl = record_ttl

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
            user_agent=get_user_agent(), **self.auth_kwargs
        )
        self.cdn_service = self.sdk.client(ResourceServiceStub)

    def get_provider_cname(self):
        if not self._provider_cname:
            self._provider_cname = self.cdn_service.GetProviderCName(
                GetProviderCNameRequest(folder_id=self.folder_id)
            ).cname
            if self._provider_cname[-1] != '.':
                self._provider_cname += '.'

        return self._provider_cname

    def process_resource(self, zone, resource, lenient=False):
        matched_domains = filter(
            lambda domain: zone.owns('CNAME', domain),
            [resource.cname, *resource.secondary_hostnames],
        )

        for fqdn in matched_domains:
            if fqdn[-1] != '.':
                fqdn = f'{fqdn}.'

            zone.add_record(
                Record.new(
                    zone,
                    zone.hostname_from_fqdn(fqdn),
                    data={
                        'type': 'CNAME',
                        'ttl': self.record_ttl,
                        'value': self.get_provider_cname(),
                    },
                    source=self,
                    lenient=lenient,
                )
            )

    def populate(self, zone, target=False, lenient=False):
        self.log.debug(
            'populate: name=%s, target=%s, lenient=%s',
            zone.name,
            target,
            lenient,
        )

        before = len(zone.records)

        done = False
        page_token = None
        while not done:
            resp = self.cdn_service.List(
                ListResourcesRequest(
                    folder_id=self.folder_id, page_token=page_token
                )
            )

            if resp.next_page_token:
                page_token = resp.next_page_token
            else:
                done = True

            for resource in resp.resources:
                self.process_resource(zone, resource, lenient)

        self.log.info('populate: found %s records', len(zone.records) - before)
