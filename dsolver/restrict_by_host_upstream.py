# -*- coding: utf-8 -*-
"""
    proxy.py
    ~~~~~~~~
    ⚡⚡⚡ Fast, Lightweight, Pluggable, TLS interception capable proxy server focused on
    Network monitoring, controls & Application development, testing, debugging.

    :copyright: (c) 2013-present by Abhinav Singh and contributors.
    :license: BSD, see LICENSE for more details.
"""
from typing import Optional
import re
from proxy.http import httpStatusCodes
from proxy.http.proxy import HttpProxyBasePlugin
from proxy.common.flag import flags
from proxy.http.parser import HttpParser
from proxy.common.utils import text_
from proxy.http.exception import HttpRequestRejected


flags.add_argument(
    '--restrict-by-host-upstream',
    type=str,
    default='facebook.com,www.facebook.com',
    help='Default: Allow Facebook.  Comma separated list of IPv4 and IPv6 addresses.',
)


class RestrictHostUpstream(HttpProxyBasePlugin):
    """Allow traffic by inspecting upstream host."""

    def before_upstream_connection(
            self, request: HttpParser,
    ) -> Optional[HttpParser]:
        if not re.match(self.flags.restrict_by_host_upstream, text_(request.host)):
            raise HttpRequestRejected(
                status_code=httpStatusCodes.I_AM_A_TEAPOT,
                reason=b'I\'m a tea pot',
            )
        return request
