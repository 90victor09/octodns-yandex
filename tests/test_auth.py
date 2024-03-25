import json
import subprocess
import tempfile

import pytest

from octodns_yandex.auth import (
    AUTH_TYPE_IAM,
    AUTH_TYPE_METADATA,
    AUTH_TYPE_OAUTH,
    AUTH_TYPE_SA_KEY,
    AUTH_TYPE_YC_CLI,
    _AuthMixin,
)
from octodns_yandex.exception import YandexCloudConfigException

STUB_TOKEN = "token"
STUB_SA_KEY = {
    'id': 'id',
    'service_account_id': 'sa_id',
    'private_key': 'base64',
}


class TestYandexCloudAuth:
    class ProcessMock:
        def __init__(self, check_error=False, stdout=None):
            self.check_error = check_error
            self._stdout = stdout

        def check_returncode(self):
            if self.check_error:
                raise subprocess.CalledProcessError(
                    returncode=1, cmd='non_existent_file'
                )

        @property
        def stdout(self):
            return self._stdout

        @property
        def returncode(self):
            return 1

    @staticmethod
    def _get_auth_kwargs(auth_type, **kwargs):
        return _AuthMixin.get_auth_kwargs(
            auth_type,
            **{
                'oauth_token': None,
                'iam_token': None,
                'sa_key_file': None,
                'sa_key': None,
                **kwargs,
            }
        )

    def test_auth_oauth(self):
        auth_kwargs = self._get_auth_kwargs(
            AUTH_TYPE_OAUTH, oauth_token=STUB_TOKEN
        )
        assert auth_kwargs.keys() == {'token'}
        assert auth_kwargs['token'] == STUB_TOKEN

    def test_auth_iam(self):
        auth_kwargs = self._get_auth_kwargs(AUTH_TYPE_IAM, iam_token=STUB_TOKEN)
        assert auth_kwargs.keys() == {'iam_token'}
        assert auth_kwargs['iam_token'] == STUB_TOKEN

    def test_auth_metadata(self):
        auth_kwargs = self._get_auth_kwargs(AUTH_TYPE_METADATA)
        assert len(auth_kwargs) == 0

    def test_auth_service_account_key(self):
        # Auth using Service Account key, provided in file
        with tempfile.NamedTemporaryFile('w+') as fp:
            json.dump(STUB_SA_KEY, fp)
            fp.flush()
            auth_kwargs = self._get_auth_kwargs(
                AUTH_TYPE_SA_KEY, sa_key_file=fp.name
            )
            assert auth_kwargs.keys() == {'service_account_key'}
            assert auth_kwargs['service_account_key'] == STUB_SA_KEY

        with pytest.raises(
            YandexCloudConfigException, match=r".*non_existent_file.*"
        ):
            self._get_auth_kwargs(
                AUTH_TYPE_SA_KEY, sa_key_file='non_existent_file'
            )

        # Auth using Service Account key, provided in config
        auth_kwargs = self._get_auth_kwargs(
            AUTH_TYPE_SA_KEY, sa_key=STUB_SA_KEY
        )
        assert auth_kwargs.keys() == {'service_account_key'}
        assert auth_kwargs['service_account_key'] == STUB_SA_KEY

        # Wrong SA key format
        del STUB_SA_KEY['id']
        with pytest.raises(
            YandexCloudConfigException, match=r".*sa_key.*fields.*"
        ):
            self._get_auth_kwargs(AUTH_TYPE_SA_KEY, sa_key=STUB_SA_KEY)

    def test_auth_cli(self, monkeypatch):
        def _not_found(*args, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: self.ProcessMock(
                stdout=STUB_TOKEN.encode('utf-8')
            ),
        )
        auth_kwargs = self._get_auth_kwargs(AUTH_TYPE_YC_CLI)
        assert auth_kwargs.keys() == {'token'}
        assert auth_kwargs['token'] == STUB_TOKEN
        monkeypatch.undo()

        monkeypatch.setattr(subprocess, "run", _not_found)
        with pytest.raises(YandexCloudConfigException):
            self._get_auth_kwargs(AUTH_TYPE_YC_CLI)
        monkeypatch.undo()

        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: self.ProcessMock(check_error=True),
        )
        with pytest.raises(YandexCloudConfigException):
            self._get_auth_kwargs(AUTH_TYPE_YC_CLI)
        monkeypatch.undo()

        # Unknown auth type
        with pytest.raises(YandexCloudConfigException):
            self._get_auth_kwargs('non_existent_type')
