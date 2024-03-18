from octodns.record import Record

from yandex.cloud.dns.v1.dns_zone_pb2 import (
    RecordSet
)

from octodns_yandex.record import YandexCloudAnameRecord


def _aname_type_map(rset):
    rset.type = YandexCloudAnameRecord._type


def _txt_unescape(rset):
    # unescape value because octodns escaping breaks escaped dkim
    for i, value in enumerate(rset.data):
        rset.data[i] = value.replace('\\;', ';')


# Custom transformers for RecordSets from API
rset_transformers = {
    'ANAME': _aname_type_map,
    'TXT': _txt_unescape,
}


def map_rset_to_octodns(provider, zone, lenient, rset):
    rset_transformers.get(rset.type, lambda *args: None)(rset)

    record_type = Record.registered_types().get(rset.type, None)
    if record_type is None:
        raise Exception('Unsupported record type')

    data = {
        'type': record_type._type,
        'ttl': rset.ttl,
    }

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
        lenient=lenient
    )


def map_octodns_to_rset(record: Record):
    values = record.data.get('values', record.data.get('value', []))
    values = values if isinstance(values, (list, tuple)) else [values]

    return RecordSet(
        name=record.fqdn,
        type=record._type.split('/')[-1],  # handle custom records
        ttl=record.ttl,
        data=[e.rdata_text for e in values]
    )
