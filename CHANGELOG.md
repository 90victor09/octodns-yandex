## v0.0.3 - 2024-03-29 - CM & CDN sources

#### Changes

* Added yandexcloud sdk version to user-agent string
* Added source for Yandex Cloud Certificate Manager (`octodns_yandex.YandexCloudCMSource`)
* Added source for Yandex Cloud CDN (`octodns_yandex.YandexCloudCDNSource`)

## v0.0.2 - 2024-03-27 - Dependencies fixes

#### Changes

* Bump minimal python version to 3.8 to match octoDNS
* Fixed python 3.12 compatibility in yandexcloud SDK
* Fixed `protobuf` package version as it is required by `googleapis-common-protos`

## v0.0.1 - 2024-03-25 - Initial release

#### Changes

* Initial implementation of YandexCloudProvider
* Initial implementation of Yandex360Provider
