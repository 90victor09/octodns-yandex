from typing import Type

from octodns.record import Record, AliasRecord, CnameRecord, \
    ARecord, AaaaRecord, CaaRecord, NsRecord, PtrRecord, SrvRecord, MxRecord, TxtRecord

from yandex.cloud.dns.v1.dns_zone_pb2 import (
    RecordSet
)

from octodns_yandex.record import YandexCloudAnameRecord


def map_one(record_type: Type[Record]):
    def handler(zone, rset):
        data = {
            'type': record_type._type,
            'ttl': rset.ttl,
            'value': record_type._value_type.parse_rdata_text(rset.data[0]),
        }

        # name = zone.hostname_from_fqdn(rset.name)
        # fqdn = rset.name
        # if 0 < len(record_type.validate(name, fqdn, data)):
        #     data['octodns'] = {'lenient': True}

        return data
    return handler


def map_multiple(record_type: Type[Record]):
    def handler(zone, rset):
        data = {
            'type': record_type._type,
            'ttl': rset.ttl,
            'values': record_type.parse_rdata_texts(rset.data)
        }
        # name = zone.hostname_from_fqdn(rset.name)
        # fqdn = rset.name
        # if 0 < len(record_type.validate(name, fqdn, data)):
        #     data['octodns'] = {'lenient': True}
        return data
    return handler

mappings = {
    'A': map_multiple(ARecord),
    'AAAA': map_multiple(AaaaRecord),
    'CAA': map_multiple(CaaRecord),
    'CNAME': map_one(CnameRecord),  # trailing .
    'ANAME': map_one(YandexCloudAnameRecord),  # trailing .
    'MX': map_multiple(MxRecord),  # trailing .
    'NS': map_multiple(NsRecord),  # trailing .
    'PTR': map_multiple(PtrRecord),  # trailing .
    'SRV': map_multiple(SrvRecord),
    'TXT': map_multiple(TxtRecord),
    # 'SVCB': ,
    # 'HTTPS': ,
}


def map_rset_to_octodns(provider, zone, lenient, rset):
    mapper = mappings.get(rset.type, None)
    if not mapper:
        raise Exception('Unsupported record type')

    return Record.new(
        zone,
        zone.hostname_from_fqdn(rset.name),
        data=mapper(zone, rset),
        source=provider,
        lenient=lenient
    )


def map_octodns_to_rset(record: Record):
    values = record.data.get('values', record.data.get('value', []))
    values = values if isinstance(values, (list, tuple)) else [values]
    return RecordSet(
        name=record.fqdn,
        type=record._type if not isinstance(record, YandexCloudAnameRecord) else "ANAME",
        ttl=record.ttl,
        data=[e.rdata_text for e in values]
    )