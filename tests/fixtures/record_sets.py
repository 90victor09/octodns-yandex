from yandex.cloud.dns.v1.dns_zone_pb2 import RecordSet
from yandex.cloud.dns.v1.dns_zone_service_pb2 import (
    ListDnsZoneRecordSetsResponse,
)

from octodns.record import Ipv6Value

# Value which key equals DNS record type should not be lenient
STUB_RECORDS = {
    'A': RecordSet(
        name="a.example.com.",
        type="A",
        ttl=300,
        data=["127.0.0.1", "127.0.0.2"],
    ),
    'AAAA': RecordSet(
        name="aaaa.example.com.",
        type="AAAA",
        ttl=300,
        # octodns simplifies IPv6
        data=[str(Ipv6Value("2001:0db8:11a3:09d7:1f34:8a2e:07a0:765d"))],
    ),
    'CAA': RecordSet(
        name="caa.example.com.",
        type="CAA",
        ttl=600,
        data=[
            "0 issue ca.example.net",
            "0 issue ca2.example.net",
            "3 asd asd",  # valid in YC
        ],
    ),
    'CAA_quoted': RecordSet(
        name="caa2.example.com.",
        type="CAA",
        ttl=600,
        data=["0 issue \"ca.example.net\""],
    ),
    'CNAME': RecordSet(
        name="cname1.example.com.",
        type="CNAME",
        ttl=3600,
        data=["example.com."],
    ),
    'CNAME_nodot': RecordSet(
        name="cname2.example.com.",
        type="CNAME",
        ttl=3600,
        data=["example.com"],  # valid in YC
    ),
    'CNAME_dot': RecordSet(
        name="cname3.example.com.",
        type="CNAME",
        ttl=600,
        data=["."],  # valid in YC
    ),
    # fmt: off
    'MX': RecordSet(
        name="mx.example.com.",
        type="MX",
        ttl=600,
        data=["10 mx.example.com."],
    ),
    'MX_nodot': RecordSet(
        name="mx2.example.com.",
        type="MX",
        ttl=600,
        data=["10 mx.example.com"],
    ),
    # fmt: on
    'NS': RecordSet(
        name="ns.example.com.",
        type="NS",
        ttl=600,
        data=["ns1.yandexcloud.net.", "ns2.yandexcloud.net."],
    ),
    'NS_root': RecordSet(
        name="example.com.",
        type="NS",
        ttl=3600,
        data=["ns1.yandexcloud.net.", "ns2.yandexcloud.net."],
    ),
    'SOA': RecordSet(
        name="example.com.",
        type="SOA",
        ttl=3600,
        data=[
            "ns1.yandexcloud.net. mx.cloud.yandex.net. 1 10800 900 604800 900"
        ],
    ),
    'PTR': RecordSet(
        name="ptr.example.com.",
        type="PTR",
        ttl=600,
        data=["example.com.", "example2.com."],
    ),
    'PTR_nodot': RecordSet(
        name="ptr2.example.com.",
        type="PTR",
        ttl=600,
        data=["example.com"],  # valid in YC
    ),
    'SRV': RecordSet(
        name="_service._tcp.example.com.",
        type="SRV",
        ttl=600,
        data=["10 70 8080 backend.example.com."],
    ),
    'SRV_nodot': RecordSet(
        name="_service2._tcp.example.com.",
        type="SRV",
        ttl=600,
        data=["10 70 8080 backend.example.com"],
    ),
    'TXT': RecordSet(
        name="txt.example.com.",
        type="TXT",
        ttl=600,
        data=[
            "test3",
            "v=DKIM1\\; k=rsa\\; s=email\\\\; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC96HHGGEenw"
            "TqEDp/ZA1ZKDkb89AVyWwyBN2ALLqtnCVffqMm9yd3N6pkW0378Jn1RxYpKttMGa7fwthMwnlN6cbo7h9wXm"
            "SRE/B7kmXtoA9QBX/5rIem11pqiP51YVNJqysMXlE6k/SPvr6KXc49s2X5jIqAE6YjI0jHUe6XDMQIDAQAB",
        ],
    ),
    # fmt: off
    'TXT_quoted': RecordSet(
        name="txt2.example.com.",
        type="TXT",
        ttl=600,
        data=["\"test\""],
    ),
    'ANAME': RecordSet(
        name="aname.example.com.",
        type="ANAME",
        ttl=600,
        data=["example.com."],
    ),
    'ANAME_nodot': RecordSet(
        name="aname2.example.com.",
        type="ANAME",
        ttl=600,
        data=["example.com"],
    ),
    'ANAME_mx': RecordSet(
        name="aname.example.com.",
        type="MX",
        ttl=600,
        data=["20 mx.example.com."],
    ),
    # fmt: on
}

IDNA_LIST_RECORD_SETS_RESPONSE_PAGE_1 = ListDnsZoneRecordSetsResponse(
    next_page_token='',
    record_sets=[
        RecordSet(
            name="xn--b1agh1afp.xn--e1aybc.xn--p1ai.",
            type="A",
            ttl=600,
            data="127.0.0.2",
        ),
        # fmt: off
        RecordSet(
            name="xn--e1aybc.xn--p1ai.",
            type="A",
            ttl=600,
            data="127.0.0.1",
        ),
        # fmt: on
        RecordSet(
            name="xn--e1aybc.xn--p1ai.",
            type="NS",
            ttl=3600,
            data="ns.internal.",
        ),
        RecordSet(
            name="xn--e1aybc.xn--p1ai.",
            type="SOA",
            ttl=3600,
            data="ns.internal. mx.cloud.yandex.net. 1 10800 900 604800 900",
        ),
    ],
)
