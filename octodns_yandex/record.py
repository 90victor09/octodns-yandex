from octodns.record import Record, ValueMixin
from octodns.record.target import _TargetValue


class YandexCloudAnameValue(_TargetValue):
    pass


# Works similar to ALIAS but allows to specify subdomains
class YandexCloudAnameRecord(ValueMixin, Record):
    _type = 'YandexCloudProvider/ANAME'
    _value_type = YandexCloudAnameValue


Record.register_type(YandexCloudAnameRecord)
