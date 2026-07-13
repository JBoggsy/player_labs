"""Runtime configuration knobs for wowborg."""

from __future__ import annotations

from dataclasses import dataclass
import os


DEFAULT_PLATFORM = "x86"
DEFAULT_OS = "Win"
DEFAULT_LOCALE = "enUS"
DEFAULT_CLIENT_SEED = 0x4B494E47
DEFAULT_PING_INTERVAL_S = 15.0
DEFAULT_LOGIN_PACKET_LIMIT = 80


@dataclass(frozen=True)
class WowborgConfig:
    """Tunable values kept out of protocol logic."""

    platform: str = DEFAULT_PLATFORM
    os_name: str = DEFAULT_OS
    locale: str = DEFAULT_LOCALE
    client_seed: int = DEFAULT_CLIENT_SEED
    ping_interval_s: float = DEFAULT_PING_INTERVAL_S
    login_packet_limit: int = DEFAULT_LOGIN_PACKET_LIMIT


def from_env() -> WowborgConfig:
    """Build config from environment variables, retaining safe defaults."""

    return WowborgConfig(
        platform=os.getenv("WOWBORG_PLATFORM", DEFAULT_PLATFORM),
        os_name=os.getenv("WOWBORG_OS", DEFAULT_OS),
        locale=os.getenv("WOWBORG_LOCALE", DEFAULT_LOCALE),
        client_seed=int(os.getenv("WOWBORG_CLIENT_SEED", str(DEFAULT_CLIENT_SEED)), 0),
        ping_interval_s=float(os.getenv("WOWBORG_PING_INTERVAL_S", str(DEFAULT_PING_INTERVAL_S))),
    )
