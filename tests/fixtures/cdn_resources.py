from google.protobuf.timestamp_pb2 import Timestamp
from yandex.cloud.cdn.v1.resource_pb2 import (
    OriginProtocol,
    Resource,
    ResourceOptions,
    SSLCertificate,
    SSLCertificateCMData,
    SSLCertificateData,
    SSLCertificateStatus,
    SSLCertificateType,
)

from tests.fixtures import STUB_FOLDER_ID

STUB_CDN_RESOURCE_1 = Resource(
    id="bc8aePai2Xajaeghoo3b",
    folder_id=STUB_FOLDER_ID,
    cname="cdn.example.com",
    created_at=Timestamp(seconds=1711558651, nanos=963842000),
    updated_at=Timestamp(seconds=1711558659, nanos=106271000),
    active=True,
    options=ResourceOptions(
        edge_cache_settings=ResourceOptions.EdgeCacheSettings(
            enabled=True, default_value=345600
        ),
        browser_cache_settings=ResourceOptions.Int64Option(
            enabled=True, value=3600
        ),
        query_params_options=ResourceOptions.QueryParamsOptions(
            ignore_query_string=ResourceOptions.BoolOption(
                enabled=True, value=True
            )
        ),
        slice=ResourceOptions.BoolOption(enabled=True, value=True),
        compression_options=ResourceOptions.CompressionOptions(
            gzip_on=ResourceOptions.BoolOption(enabled=True)
        ),
        redirect_options=ResourceOptions.RedirectOptions(
            redirect_http_to_https=ResourceOptions.BoolOption(
                enabled=True, value=True
            )
        ),
        host_options=ResourceOptions.HostOptions(
            host=ResourceOptions.StringOption(
                enabled=True, value="origin.example.com"
            )
        ),
        static_headers=ResourceOptions.StringsMapOption(enabled=True),
        cors=ResourceOptions.StringsListOption(
            enabled=True, value=["domain1.example.com", "domain2.example.com"]
        ),
        stale=ResourceOptions.StringsListOption(
            enabled=True, value=["error", "updating"]
        ),
        allowed_http_methods=ResourceOptions.StringsListOption(
            enabled=True, value=["GET", "OPTIONS", "HEAD"]
        ),
        static_request_headers=ResourceOptions.StringsMapOption(enabled=True),
        ignore_cookie=ResourceOptions.BoolOption(enabled=True, value=True),
    ),
    origin_group_id=123456,
    origin_group_name="Stub group name 1",
    origin_protocol=OriginProtocol.HTTPS,
    ssl_certificate=SSLCertificate(
        type=SSLCertificateType.CM,
        status=SSLCertificateStatus.READY,
        data=SSLCertificateData(
            cm=SSLCertificateCMData(id="fpqzonu0haing3eegiet")
        ),
    ),
)
STUB_CDN_RESOURCE_2 = Resource(
    id="bc8ceeChozee1aCohcau",
    folder_id=STUB_FOLDER_ID,
    cname="cdn.example.com",
    created_at=Timestamp(seconds=1711558669, nanos=728117000),
    updated_at=Timestamp(seconds=1711558678, nanos=912906000),
    active=True,
    options=ResourceOptions(
        edge_cache_settings=ResourceOptions.EdgeCacheSettings(
            enabled=True, default_value=345600
        ),
        query_params_options=ResourceOptions.QueryParamsOptions(
            ignore_query_string=ResourceOptions.BoolOption(enabled=True)
        ),
        slice=ResourceOptions.BoolOption(enabled=True),
        compression_options=ResourceOptions.CompressionOptions(
            gzip_on=ResourceOptions.BoolOption(enabled=True, value=True)
        ),
        redirect_options=ResourceOptions.RedirectOptions(
            redirect_http_to_https=ResourceOptions.BoolOption(
                enabled=True, value=True
            )
        ),
        host_options=ResourceOptions.HostOptions(
            forward_host_header=ResourceOptions.BoolOption(
                enabled=True, value=True
            )
        ),
        static_headers=ResourceOptions.StringsMapOption(enabled=True),
        stale=ResourceOptions.StringsListOption(
            enabled=True, value=["error", "updating"]
        ),
        static_request_headers=ResourceOptions.StringsMapOption(enabled=True),
        ignore_cookie=ResourceOptions.BoolOption(enabled=True, value=True),
    ),
    secondary_hostnames=["cdn2.example.com."],
    origin_group_id=123457,
    origin_group_name="Stub group name 2",
    origin_protocol=OriginProtocol.HTTPS,
    ssl_certificate=SSLCertificate(
        type=SSLCertificateType.CM,
        status=SSLCertificateStatus.READY,
        data=SSLCertificateData(
            cm=SSLCertificateCMData(id="fpqnu9yohveig8ahm2je")
        ),
    ),
)
