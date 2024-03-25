from google.protobuf.timestamp_pb2 import Timestamp
from yandex.cloud.dns.v1.dns_zone_pb2 import (
    DnsZone,
    PrivateVisibility,
    PublicVisibility,
)

STUB_ZONE_NAME = "example.com."

STUB_NETWORK_ID = 'bie1YohT6ahmicoshohb'
STUB_FOLDER_ID = "oogiy4eivee6faegouRu"

STUB_ZONE_1 = DnsZone(
    id='dnsisei4peetahsak6oh',
    folder_id=STUB_FOLDER_ID,
    created_at=Timestamp(seconds=1710685039, nanos=779000000),
    name="test2",
    zone=STUB_ZONE_NAME,
    private_visibility=PrivateVisibility(network_ids=[STUB_NETWORK_ID]),
)

STUB_ZONE_2 = DnsZone(
    id='dnsh5athi0ha3di4eiv6',
    folder_id=STUB_FOLDER_ID,
    created_at=Timestamp(seconds=1710685015, nanos=601000000),
    name="test",
    zone=STUB_ZONE_NAME,
    private_visibility=PrivateVisibility(),
)

STUB_ZONE_PUBLIC = DnsZone(
    id='dnsg8coh3cheiBahpohk',
    folder_id=STUB_FOLDER_ID,
    created_at=Timestamp(seconds=1710325719, nanos=138000000),
    name="example-com",
    zone=STUB_ZONE_NAME,
    public_visibility=PublicVisibility(),
)


STUB_IDNA_ZONE_NAME = "xn--e1aybc.xn--p1ai."

STUB_IDNA_ZONE = DnsZone(
    id='dnshahmeep0hei5aighe',
    folder_id=STUB_FOLDER_ID,
    created_at=Timestamp(seconds=1710779521, nanos=553000000),
    name="idna-test",
    description="An idna test",
    zone=STUB_IDNA_ZONE_NAME,
    private_visibility=PrivateVisibility(),
)
