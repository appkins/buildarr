# Copyright (C) 2024 Callum Dickinson
#
# Buildarr is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# Buildarr is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with Buildarr.
# If not, see <https://www.gnu.org/licenses/>.


"""
Dummy2 plugin secrets file model.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Optional

from pydantic import validator

from buildarr.secrets import SecretsPlugin
from buildarr.types import NonEmptyStr, Port

from .api import api_get
from .exceptions import Dummy2APIError
from .types import Dummy2Protocol

# Allow Mypy to properly resolve configuration type declarations in secrets classes.
if TYPE_CHECKING:
    from typing_extensions import Self

    from .config import Dummy2Config

    class _Dummy2Secrets(SecretsPlugin[Dummy2Config]):
        pass

else:

    class _Dummy2Secrets(SecretsPlugin):
        pass


class Dummy2Secrets(_Dummy2Secrets):
    """
    Dummy2 API secrets.
    """

    hostname: NonEmptyStr
    port: Port
    protocol: Dummy2Protocol
    url_base: Optional[str]
    version: NonEmptyStr

    @property
    def host_url(self) -> str:
        """
        Full host URL for the Dummy instance.
        """
        return self._get_host_url(
            protocol=self.protocol,
            hostname=self.hostname,
            port=self.port,
            url_base=self.url_base,
        )

    @validator("url_base")
    def validate_url_base(cls, value: Optional[str]) -> Optional[str]:
        """
        Process the defined `url_base` value, and make sure the value in the secrets objects
        is consistently formatted.

        Args:
            value (Optional[str]): `url_base` value.

        Returns:
            Validated value
        """
        return f"/{value.strip('/')}" if value and value.strip("/") else None

    @classmethod
    def _get_host_url(
        cls,
        protocol: str,
        hostname: str,
        port: int,
        url_base: Optional[str],
    ) -> str:
        """
        Helper method to create a fully-qualified host URL.

        Args:
            hostname (str): Instance hostname.
            port (int): Instance access port.
            protocol (str): Instance access protocol.
            url_base (Optional[str], optional): Instance URL base.

        Returns:
            Full host URL
        """
        return f"{protocol}://{hostname}:{port}{cls.validate_url_base(url_base) or ''}"

    @classmethod
    def get(cls, config: Dummy2Config) -> Self:
        """
        Generate a secrets object from the given instance configuration,
        retrieving any necessary secrets in the process.

        Args:
            config (DummyConfig): Instance configuration.

        Returns:
            Secrets object
        """
        return cls.get_from_url(
            hostname=config.hostname,
            port=config.port,
            protocol=config.protocol,
            url_base=config.url_base,
        )

    @classmethod
    def get_from_url(
        cls,
        hostname: str,
        port: int,
        protocol: str,
        url_base: Optional[str] = None,
    ) -> Self:
        """
        Generate a secrets object from the given instance access details,
        retrieving any necessary secrets in the process.

        Args:
            hostname (str): Instance hostname.
            port (int): Instance access port.
            protocol (str): Instance access protocol.
            url_base (Optional[str], optional): Instance URL base. Default is `None`.

        Returns:
            Secrets object
        """
        url_base = cls.validate_url_base(url_base)
        host_url = cls._get_host_url(
            protocol=protocol,
            hostname=hostname,
            port=port,
            url_base=url_base,
        )
        initialize_json = api_get(host_url, "/initialize.json")
        return cls(
            hostname=hostname,
            port=port,
            protocol=protocol,
            url_base=url_base,
            version=initialize_json["version"],
        )

    def test(self) -> bool:
        """
        Test whether or not the secrets metadata is valid for connecting to the instance.

        Returns:
            `True` if the test was successful, otherwise `False`
        """
        try:
            api_get(self.host_url, "/api/v1/status")
        except Dummy2APIError as err:
            if err.status_code == HTTPStatus.UNAUTHORIZED:
                return False
            else:
                raise
        else:
            return True