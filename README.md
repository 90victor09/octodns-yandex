[![PyPI Version][pypi-image]][pypi-url]
[![Build Status][build-image]][build-url]
[![License][license-image]][license-url]

<!-- Badges -->

[pypi-image]: https://img.shields.io/pypi/v/octodns-yandex
[pypi-url]: https://pypi.org/project/octodns-yandex/
[build-image]: https://github.com/90victor09/octodns-yandex/actions/workflows/main.yml/badge.svg
[build-url]: https://github.com/90victor09/octodns-yandex/actions/workflows/main.yml
[license-image]: https://img.shields.io/github/license/90victor09/octodns-yandex.svg
[license-url]: https://github.com/90victor09/octodns-yandex/blob/master/LICENSE

## YandexCloud DNS provider for octoDNS

An (unofficial) [octoDNS](https://github.com/octodns/octodns/) provider that targets [Yandex Cloud DNS](https://cloud.yandex.com/en/services/dns).

And an additional provider for [Yandex 360 for business](https://360.yandex.com/business/).

### Installation

#### Command line

```
pip install octodns-yandex
```

#### requirements.txt/setup.py

Pinning specific versions or SHAs is recommended to avoid unplanned upgrades.

##### Versions

```
# Start with the latest versions and don't just copy what's here
octodns==1.6.1
octodns-yandex==0.0.3
```

##### SHAs

```
# Start with the latest/specific versions and don't just copy what's here
-e git+https://git@github.com/octodns/octodns.git@384ce2018291f15c1d021a70f46820315af478cc#egg=octodns
-e git+https://git@github.com/90victor09/octodns-yandex.git@0067b545710050b7e4f85471bbe7bfe66a6a0c10#egg=octodns_yandex
```

### Configuration

#### Yandex Cloud Provider

Required roles:
- `dns.editor` - for dump and sync
- `dns.viewer` - for dump only

```yaml
providers:
  yandexcloud:
    class: octodns_yandex.YandexCloudProvider
    # Cloud folder id to look up DNS zones
    folder_id: a1bc...
    # YandexCloud allows creation of multiple zones with the same name.
    #  By default, provider picks first found zone (null)
    #  You can specify to search public zone, if it exists (true)
    #  Or first found internal zone (false)
    # If you have several internal zones with the same name - see zone_ids_map
    prioritize_public: true
    # Optionally, provide ids to map zones exactly
    zone_ids_map:
      example.com.: dns1abc...

    # Auth type. Available options:
    #  oauth - use OAuth token
    #  iam - use IAM token
    #  metadata - automatic auth inside of VM instance/function with assigned Service Account
    #  sa-key - use Service Account Key
    #  yc-cli - call 'yc' command to get OAuth token from its config
    auth_type: yc-cli
    # (oauth) OAuth token
    #oauth_token: env/YC_OAUTH_TOKEN
    # (iam) IAM token
    #iam_token: env/YC_IAM_TOKEN
    # (sa-key) File with SA key JSON
    #sa_key_file: key.json
    # (sa-key) Or, its in-config values
    #sa_key:
    #  id: env/YC_SA_KEY_ID
    #  service_account_id: env/YC_SA_KEY_ACCOUNT_ID
    #  private_key: env/YC_SA_KEY_PRIVATE_KEY
```

#### Yandex Cloud CM Source

Provides records for ACME DNS challenges.

Required role:
- `certificate-manager.viewer`

```yaml
providers:
  yandexcloud_cm:
    class: octodns_yandex.YandexCloudCMSource
    # Cloud folder id to look up DNS zones
    folder_id: a1bc...
    # Challenge type to use: CNAME or TXT
    record_type: CNAME
    # Challenge records TTL
    record_ttl: 3600

    # Auth options are the same as for octodns_yandex.YandexCloudProvider
    auth_type: yc-cli
```

#### Yandex Cloud CDN Source

Provides CNAME records for CDN.

Required role:
- `cdn.viewer`

```yaml
providers:
  yandexcloud_cdn:
    class: octodns_yandex.YandexCloudCDNSource
    # Cloud folder id to look up DNS zones
    folder_id: a1bc...
    # CDN records TTL
    record_ttl: 3600

    # Auth options are the same as for octodns_yandex.YandexCloudProvider
    auth_type: yc-cli
```

#### Yandex 360

You can obtain OAuth token through existing application:  
https://oauth.yandex.ru/authorize?response_type=token&client_id=daf031bc5d83471d88c5932e8ddef46c

Or you can [create your own application](https://yandex.ru/dev/api360/doc/concepts/access.html) with following permissions:
- `directory:read_organization`
- `directory:read_domains`
- `directory:manage_dns`

```yaml
providers:
  yandex360:
    class: octodns_yandex.Yandex360Provider
    # OAuth token
    oauth_token: env/Y360_TOKEN
```

### Support Information

#### Records

| What                   | Supported records                                                     |
|------------------------|-----------------------------------------------------------------------|
| `YandexCloudProvider`  | `A`, `AAAA`, `CAA`, `CNAME`, `MX`, `NS`, `PTR`, `SRV`, `TXT`, `ANAME` |
| `Yandex360Provider`    | `A`, `AAAA`, `CAA`, `CNAME`, `MX`, `NS`, `SRV`, `TXT`                 |
| `YandexCloudCMSource`  | `CNAME`, `TXT`                                                        |
| `YandexCloudCDNSource` | `CNAME`                                                               |

#### Root NS Records

`YandexCloudProvider` supports root NS record management, but changing them doesn't seem to do anything.

`Yandex360Provider` does not support root NS record management.

#### Dynamic

`YandexCloudProvider` does not support dynamic records.

`Yandex360Provider` does not support dynamic records.

#### Provider Specific Types

`YandexCloudProvider/ANAME` record acts like `ALIAS`, but supports subdomains.
```yaml
aname:
  type: YandexCloudProvider/ANAME
  value: example.com.
```

### Development

See the [/script/](/script/) directory for some tools to help with the development process. They generally follow the [Script to rule them all](https://github.com/github/scripts-to-rule-them-all) pattern. Most useful is `./script/bootstrap` which will create a venv and install both the runtime and development related requirements. It will also hook up a pre-commit hook that covers most of what's run by CI.

If you are using PyCharm with `yc-cli` auth type, it could be easier to create a symlink to 'yc' binary in your venv's bin directory rather than trying to get it working the proper way :/ .
