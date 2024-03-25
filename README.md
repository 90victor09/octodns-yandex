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
octodns==0.9.14
octodns-yandex==0.0.1
```

##### SHAs

```
# Start with the latest/specific versions and don't just copy what's here
-e git+https://git@github.com/octodns/octodns.git@9da19749e28f68407a1c246dfdf65663cdc1c422#egg=octodns
-e git+https://git@github.com/90victor09/octodns-yandex.git@ec9661f8b335241ae4746eea467a8509205e6a30#egg=octodns_yandex
```

### Configuration

#### Yandex Cloud Provider

Required role:
- `dns.editor`

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

| What                  | Supported records                                                     |
|-----------------------|-----------------------------------------------------------------------|
| `YandexCloudProvider` | `A`, `AAAA`, `CAA`, `CNAME`, `MX`, `NS`, `PTR`, `SRV`, `TXT`, `ANAME` |
| `Yandex360Provider`   | `A`, `AAAA`, `CAA`, `CNAME`, `MX`, `NS`, `SRV`, `TXT`                 |

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
