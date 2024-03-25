from octodns.record import Ipv6Value


def make_cursor_resp(page_token, **kwargs):
    return {'nextPageToken': page_token, **kwargs}


def make_paginated_resp(page, pages, per_page, total, **kwargs):
    return {
        'page': page,
        'pages': pages,
        'perPage': per_page,
        'total': total,
        **kwargs,
    }


STUB_ORG_1 = {
    'id': 1234,
    'name': 'example.com',
    'email': '',
    'phone': '',
    'fax': '',
    'language': 'ru',
    'subscriptionPlan': 'free',
}

STUB_ORG_2 = {
    'id': 1235,
    'name': 'example2.com',
    'email': '',
    'phone': '',
    'fax': '',
    'language': 'ru',
    'subscriptionPlan': 'free',
}


STUB_DOMAIN_1 = {
    'name': 'example.com',
    'country': 'ru',
    'mx': False,
    'delegated': False,
    'master': True,
    'verified': True,
    'status': {
        'name': 'example.com',
        'spf': {'match': False, 'value': 'v=spf1 mx a -all'},
        'mx': {'match': False, 'value': 'host=mx.example.com priority=0'},
        'ns': {'match': False, 'value': 'ns1.example.com\nns2.example.com'},
        'dkim': {
            'match': True,
            'value': 'v=DKIM1; k=rsa; t=s; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDK1bS'
            '7mNooVu1/GB8FKDwp3gxjzFCUeAz60IM7KOIsOhqFiVqkvr7zV35C5FLwsx6buJbpl'
            'AcgTjvLzKwgDfldUsStjkmIxMHNFY9uXF/+4Go/wXLpe5SwAsXdmAe7IOeu27Issyr'
            'PJ74WYE+3iAeByChXYIcY7oHEthcfwlQk8wIDAQAB',
        },
        'lastCheck': '2024-03-23T07:39:41.945Z',
        'lastAdded': '2024-03-20T14:23:46.931Z',
    },
}
STUB_DOMAIN_2 = {
    'name': 'ya360.example.com',
    'country': 'ru',
    'mx': True,
    'delegated': True,
    'master': False,
    'verified': True,
}

# Every value should be a set of entries resulting in single Record
# Value which key equals DNS record type should not be lenient
STUB_ENTRIES = {
    'A': [
        {
            'recordId': 1,
            'type': 'A',
            'name': 'a',
            'ttl': 600,
            'address': '127.0.0.1',
        },
        {
            'recordId': 2,
            'type': 'A',
            'name': 'a',
            'ttl': 600,
            'address': '127.0.0.2',
        },
    ],
    'A_single': [
        {
            'recordId': 3,
            'type': 'A',
            'name': 'a1',
            'ttl': 600,
            'address': '127.0.0.1',
        }
    ],
    'AAAA': [
        {
            'recordId': 4,
            'type': 'AAAA',
            'name': 'aaaa',
            'ttl': 300,
            'address': str(
                Ipv6Value('2001:0db8:11a3:09d7:1f34:8a2e:07a0:765d')
            ),
        },
        {
            'recordId': 5,
            'type': 'AAAA',
            'name': 'aaaa',
            'ttl': 350,
            'address': str(
                Ipv6Value('2001:0db8:11a3:09d7:1f34:8a2e:07a0:766d')
            ),
        },
    ],
    'AAAA_triple': [
        {
            'recordId': 6,
            'type': 'AAAA',
            'name': 'aaaa3',
            'ttl': 300,
            'address': str(
                Ipv6Value('2001:0db8:11a3:09d7:1f34:8a2e:07a0:765d')
            ),
        },
        {
            'recordId': 7,
            'type': 'AAAA',
            'name': 'aaaa3',
            'ttl': 350,
            'address': str(
                Ipv6Value('2001:0db8:11a3:09d7:1f34:8a2e:07a0:766d')
            ),
        },
        {
            'recordId': 8,
            'type': 'AAAA',
            'name': 'aaaa3',
            'ttl': 350,
            'address': str(
                Ipv6Value('2001:0db8:11a3:09d7:1f34:8a2e:07a0:767d')
            ),
        },
    ],
    'AAAA_second_record': [
        {
            'recordId': 9,
            'type': 'AAAA',
            'name': 'a',
            'ttl': 600,
            'address': '::1',
        }
    ],
    'CNAME': [
        {
            'recordId': 10,
            'type': 'CNAME',
            'name': 'cname',
            'ttl': 600,
            'target': 'example.com.',
        }
    ],
    'CNAME_mail': [
        {
            'recordId': 11,
            'type': 'CNAME',
            'name': 'mail',
            'ttl': 21600,
            'target': 'domain.mail.yandex.net.',
        }
    ],
    'MX': [
        {
            'recordId': 12,
            'type': 'MX',
            'name': '@',
            'ttl': 21600,
            'exchange': 'mx.yandex.net.',
            'preference': 10,
        }
    ],
    'TXT': [
        {
            'recordId': 13,
            'type': 'TXT',
            'name': 'txt',
            'ttl': 600,
            'text': 'Hello world',
        }
    ],
    'TXT_dkim': [
        {
            'recordId': 14,
            'type': 'TXT',
            'name': 'mail._domainkey',
            'ttl': 21600,
            'text': 'v=DKIM1; k=rsa\\\\; t=s; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ'
            'KBgQDK1bS7mNooVu1/GB8FKDwp3gxjzFCUeAz60IM7KOIsOhqFiVqkvr7zV35C5FLwsx6'
            'buJbplAcgTjvLzKwgDfldUsStjkmIxMHNFY9uXF/+4Go/wXLpe5SwAsXdmAe7IOeu27Is'
            'syrPJ74WYE+3iAeByChXYIcY7oHEthcfwlQk8wIDAQAB',
        }
    ],
    'TXT_spf': [
        {
            'recordId': 15,
            'type': 'TXT',
            'name': '@',
            'ttl': 21600,
            'text': 'v=spf1 redirect=_spf.yandex.net',
        }
    ],
    'SRV': [
        {
            'recordId': 16,
            'type': 'SRV',
            'name': '_service._tcp',
            'ttl': 600,
            'target': 'backend.example.com.',
            'port': 8080,
            'priority': 10,
            'weight': 70,
        }
    ],
    'NS': [
        {
            'recordId': 17,
            'type': 'NS',
            'name': 'ns',
            'ttl': 600,
            'target': 'ns1.example.com.',
        },
        {
            'recordId': 18,
            'type': 'NS',
            'name': 'ns',
            'ttl': 600,
            'target': 'ns2.example.com.',
        },
    ],
    'CAA': [
        {
            'recordId': 19,
            'type': 'CAA',
            'name': 'caa',
            'ttl': 600,
            'flag': 0,
            'tag': 'issue',
            'value': 'ca.example.net',
        }
    ],
}
