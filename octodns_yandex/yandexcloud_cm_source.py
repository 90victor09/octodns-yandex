from logging import getLogger

import yandexcloud
from yandex.cloud.certificatemanager.v1.certificate_pb2 import (
    CertificateType,
    ChallengeType,
)
from yandex.cloud.certificatemanager.v1.certificate_service_pb2 import (
    ListCertificatesRequest,
)
from yandex.cloud.certificatemanager.v1.certificate_service_pb2_grpc import (
    CertificateServiceStub,
)

from octodns import __VERSION__ as octodns_version
from octodns.record import Record
from octodns.source.base import BaseSource

from octodns_yandex.auth import _AuthMixin
from octodns_yandex.exception import YandexCloudConfigException
from octodns_yandex.version import __VERSION__ as provider_version


class YandexCloudCMSource(_AuthMixin, BaseSource):
    SUPPORTS_GEO = False
    SUPPORTS = {'CNAME', 'TXT'}

    def __init__(
        self,
        id,
        folder_id: str,
        auth_type: str,
        record_type='CNAME',
        record_ttl=3600,
        oauth_token=None,
        iam_token=None,
        sa_key_file=None,
        sa_key=None,
        *args,
        **kwargs,
    ):
        self.log = getLogger(f"YandexCloudCMSource[{id}]")

        self.folder_id = folder_id
        self.record_type = record_type
        if record_type not in self.SUPPORTS:
            raise YandexCloudConfigException('Not supported record_type')
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
            user_agent=f"octodns/{octodns_version} octodns-yandex/{provider_version}",
            **self.auth_kwargs,
        )
        self.cm_service = self.sdk.client(CertificateServiceStub)

    def process_certificate(self, zone, cert, lenient=False):
        if cert.type != CertificateType.MANAGED:
            return

        if not next(
            (x for x in cert.domains if zone.owns(self.record_type, x)), None
        ):
            return

        for challenge in cert.challenges:
            if challenge.type != ChallengeType.DNS:
                continue

            challenge_record = challenge.dns_challenge
            if challenge_record.type != self.record_type:
                continue

            if not zone.owns(self.record_type, challenge_record.name):
                continue

            new_record = Record.new(
                zone,
                zone.hostname_from_fqdn(challenge_record.name),
                data={
                    'type': challenge_record.type,
                    'ttl': self.record_ttl,
                    'value': challenge_record.value,
                },
                source=self,
                lenient=lenient,
            )

            # If there is already same record exists - skip
            # (possible when requesting cert for domain and its wildcard)
            if new_record in zone.records:
                continue

            zone.add_record(new_record)

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
            resp = self.cm_service.List(
                ListCertificatesRequest(
                    folder_id=self.folder_id, view='FULL', page_token=page_token
                )
            )

            if resp.next_page_token:
                page_token = resp.next_page_token
            else:
                done = True

            for cert in resp.certificates:
                self.process_certificate(zone, cert, lenient)

        self.log.info('populate: found %s records', len(zone.records) - before)
