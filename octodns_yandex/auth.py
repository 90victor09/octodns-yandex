import json
import subprocess

from octodns_yandex.exception import YandexCloudConfigException

AUTH_TYPE_OAUTH = 'oauth'
AUTH_TYPE_IAM = 'iam'
AUTH_TYPE_METADATA = 'metadata'
AUTH_TYPE_SA_KEY = 'sa-key'
AUTH_TYPE_YC_CLI = 'yc-cli'


class _AuthMixin(object):
    @staticmethod
    def get_auth_kwargs(auth_type, oauth_token, iam_token, sa_key_file, sa_key):
        if auth_type == AUTH_TYPE_OAUTH:
            return {'token': oauth_token}
        elif auth_type == AUTH_TYPE_IAM:
            return {'iam_token': iam_token}
        elif auth_type == AUTH_TYPE_METADATA:
            return {}  # Autoconfigured by SDK
        elif auth_type == AUTH_TYPE_SA_KEY:
            if sa_key_file:
                try:
                    with open(sa_key_file) as infile:
                        sa_key = json.load(infile)
                except OSError as e:
                    raise YandexCloudConfigException(
                        f"Failed to open 'sa_key_file': {sa_key_file}"
                    ) from e
            if (
                sa_key is None
                or 'id' not in sa_key
                or 'service_account_id' not in sa_key
                or 'private_key' not in sa_key
            ):
                raise YandexCloudConfigException(
                    "Provider option 'sa_key' should be dict with fields: id, service_account_id, private_key"
                )
            return {'service_account_key': sa_key}
        elif auth_type == AUTH_TYPE_YC_CLI:
            process = None
            try:
                process = subprocess.run(
                    ['yc', 'config', 'get', 'token'], stdout=subprocess.PIPE
                )
                process.check_returncode()
            except FileNotFoundError as e:
                raise YandexCloudConfigException(
                    'yc binary not found in PATH'
                ) from e
            except subprocess.CalledProcessError as e:
                raise YandexCloudConfigException(
                    f"Failed to get token from yc, exit code: {process.returncode}"
                ) from e

            return {'token': process.stdout.decode('utf-8').strip()}
        else:
            raise YandexCloudConfigException("Unknown auth type")
