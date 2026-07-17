from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Callable, Iterable, Optional
from urllib.parse import parse_qsl, urljoin, urlparse, urlunparse


class DestinationError(ValueError):
    pass


ResolveFn = Callable[[str], Iterable[tuple]]


@dataclass(frozen=True)
class ResolvedTarget:
    url: str
    scheme: str
    host: str
    port: int
    addresses: tuple[str, ...]


class DestinationGuard:
    def __init__(
        self,
        *,
        allowed_schemes: tuple[str, ...] = ("https", "http"),
        deny_private: bool = True,
        fixture_mode: bool = False,
        resolve: Optional[ResolveFn] = None,
        max_redirects: int = 5,
    ) -> None:
        self.allowed_schemes = allowed_schemes
        self.deny_private = deny_private
        self.fixture_mode = fixture_mode
        self.resolve = resolve or socket.getaddrinfo
        self.max_redirects = max_redirects

    def validate_url(self, url: str) -> ResolvedTarget:
        parsed = urlparse(url)
        if parsed.scheme not in self.allowed_schemes:
            raise DestinationError(f"scheme not allowed: {parsed.scheme}")
        if not parsed.hostname:
            raise DestinationError("missing host")
        if parsed.username or parsed.password:
            raise DestinationError("userinfo forbidden")
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if host.lower() in {"metadata.google.internal", "metadata.goog"}:
            raise DestinationError("metadata host blocked")
        addrs: list[str] = []
        try:
            infos = self.resolve(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise DestinationError(f"dns failed: {exc}") from exc
        for info in infos:
            ip = info[4][0]
            addrs.append(ip)
            self._assert_ip_allowed(ip)
        if self.deny_private and not self.fixture_mode:
            # hostnames that look local even before resolve
            if host.lower() in {"localhost"} or host.endswith(".local"):
                raise DestinationError("local host blocked")
        return ResolvedTarget(
            url=url,
            scheme=parsed.scheme,
            host=host,
            port=port,
            addresses=tuple(sorted(set(addrs))),
        )

    def validate_redirect(self, previous: ResolvedTarget, location: str) -> ResolvedTarget:
        next_url = urljoin(previous.url, location)
        return self.validate_url(next_url)

    def _assert_ip_allowed(self, ip_text: str) -> None:
        if not self.deny_private:
            return
        if self.fixture_mode:
            # fixture mode may allow loopback only
            ip = ipaddress.ip_address(ip_text)
            if ip.is_loopback:
                return
        ip = ipaddress.ip_address(ip_text)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise DestinationError(f"private/non-public address blocked: {ip_text}")
        # CGNAT / metadata-ish ranges
        if ip.version == 4:
            n = int(ip)
            # 100.64.0.0/10
            if (n & 0xFFC00000) == 0x64400000:
                raise DestinationError("cgnat address blocked")
            # 169.254.169.254
            if str(ip) == "169.254.169.254":
                raise DestinationError("metadata address blocked")

    def normalize_for_artifact(self, url: str) -> str:
        parsed = urlparse(url)
        # drop query/fragment and redact sensitive path segments
        path_parts = []
        for part in parsed.path.split("/"):
            if not part:
                continue
            low = part.lower()
            if any(
                token in low
                for token in ("token", "session", "account", "user", "id", "otp")
            ) and any(ch.isdigit() for ch in part):
                path_parts.append("[REDACTED]")
            else:
                path_parts.append(part)
        path = "/" + "/".join(path_parts) if path_parts else ""
        return urlunparse((parsed.scheme, parsed.netloc.split("@")[-1], path, "", "", ""))
