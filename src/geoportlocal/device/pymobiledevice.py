"""Current pymobiledevice3 integration for GeoPortLocal."""

from __future__ import annotations

from contextlib import AsyncExitStack

from pymobiledevice3 import usbmux
from pymobiledevice3.exceptions import (
    ConnectionTerminatedError,
    DeveloperModeIsNotEnabledError,
    DeviceNotFoundError,
    DeviceVersionNotSupportedError,
    DvtException,
    InvalidServiceError,
    MuxException,
    NoDeviceConnectedError,
    NotConnectedError,
    NotPairedError,
    NotTrustedError,
    PairingDialogResponsePendingError,
    PyMobileDevice3Exception,
    RSDRequiredError,
    TunneldConnectionError,
    UserDeniedPairingError,
    UserspaceTunnelUnavailableError,
)
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.remote.rsd_tunnel import PreferredRsdTunnel
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

from geoportlocal.device.adapter import DeviceConnection
from geoportlocal.domain.device import ConnectionKind, DeviceDescriptor, Location
from geoportlocal.domain.errors import ErrorCode, GeoPortError

_MIN_MODERN_IOS = (17, 4)
_PAIR_TIMEOUT_SECONDS = 15.0


class PymobileDeviceConnection(DeviceConnection):
    """Own the complete RSD -> DVT -> location-simulation context stack."""

    def __init__(
        self,
        descriptor: DeviceDescriptor,
        stack: AsyncExitStack,
        location_service: LocationSimulation,
    ) -> None:
        self._descriptor = descriptor
        self._stack = stack
        self._location_service = location_service
        self._closed = False

    @property
    def descriptor(self) -> DeviceDescriptor:
        return self._descriptor

    @classmethod
    async def open(cls, descriptor: DeviceDescriptor) -> PymobileDeviceConnection:
        stack = AsyncExitStack()
        await stack.__aenter__()

        try:
            rsd = await stack.enter_async_context(
                PreferredRsdTunnel(serial=descriptor.identifier, autopair=True)
            )
            dvt = await stack.enter_async_context(DvtProvider(rsd))
            location_service = await stack.enter_async_context(LocationSimulation(dvt))
        except Exception as exc:
            await stack.aclose()
            raise _translate_exception(exc, operation="connect") from exc

        return cls(descriptor, stack, location_service)

    async def set_location(self, location: Location) -> None:
        self._ensure_open()
        try:
            await self._location_service.set(location.latitude, location.longitude)
        except Exception as exc:
            raise _translate_exception(exc, operation="set") from exc

    async def clear_location(self) -> None:
        self._ensure_open()
        try:
            await self._location_service.clear()
        except Exception as exc:
            raise _translate_exception(exc, operation="clear") from exc

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self._stack.aclose()
        except Exception as exc:
            raise _translate_exception(exc, operation="disconnect") from exc

    def _ensure_open(self) -> None:
        if self._closed:
            raise GeoPortError(
                ErrorCode.DEVICE_DISCONNECTED,
                "The selected device session is already closed.",
                retryable=True,
            )


class PymobileDeviceAdapter:
    """Discover and connect iOS devices using pymobiledevice3 public library APIs."""

    async def discover(self) -> list[DeviceDescriptor]:
        try:
            mux_devices = await usbmux.list_devices()
        except Exception as exc:
            raise _translate_exception(exc, operation="discover") from exc

        # usbmux can expose the same device through USB and network transports.
        # Prefer USB for a local desktop workflow and return one row per identifier.
        preferred: dict[str, usbmux.MuxDevice] = {}
        for mux_device in mux_devices:
            existing = preferred.get(mux_device.serial)
            if existing is None or (mux_device.is_usb and not existing.is_usb):
                preferred[mux_device.serial] = mux_device

        descriptors: list[DeviceDescriptor] = []
        for identifier, mux_device in preferred.items():
            descriptors.append(await self._describe(identifier, mux_device.connection_type))
        return descriptors

    async def connect(self, identifier: str) -> PymobileDeviceConnection:
        mux_device = await self._find_device(identifier)

        try:
            async with await create_using_usbmux(
                serial=identifier,
                connection_type=mux_device.connection_type,
                autopair=True,
                pair_timeout=_PAIR_TIMEOUT_SECONDS,
            ) as lockdown:
                descriptor = _descriptor_from_lockdown(
                    identifier,
                    mux_device.connection_type,
                    lockdown.short_info,
                )
                _require_modern_ios(descriptor)

                developer_mode_enabled = await lockdown.get_developer_mode_status()
                if not developer_mode_enabled:
                    raise GeoPortError(
                        ErrorCode.DEVELOPER_MODE_REQUIRED,
                        "Developer Mode must be enabled on the selected iOS device.",
                        retryable=True,
                    )
        except GeoPortError:
            raise
        except Exception as exc:
            raise _translate_exception(exc, operation="connect") from exc

        return await PymobileDeviceConnection.open(descriptor)

    async def _find_device(self, identifier: str) -> usbmux.MuxDevice:
        try:
            devices = [
                device
                for device in await usbmux.list_devices()
                if device.serial == identifier
            ]
        except Exception as exc:
            raise _translate_exception(exc, operation="discover") from exc

        if not devices:
            raise GeoPortError(
                ErrorCode.DEVICE_NOT_FOUND,
                "The selected iOS device is no longer connected.",
                retryable=True,
            )

        return next((device for device in devices if device.is_usb), devices[0])

    async def _describe(self, identifier: str, connection_type: str) -> DeviceDescriptor:
        baseline = DeviceDescriptor(
            identifier=identifier,
            connection=_connection_kind(connection_type),
        )

        try:
            async with await create_using_usbmux(
                serial=identifier,
                connection_type=connection_type,
                autopair=False,
            ) as lockdown:
                return _descriptor_from_lockdown(identifier, connection_type, lockdown.short_info)
        except Exception:
            # Physical discovery remains useful even when the phone is locked, untrusted,
            # rebooting or metadata is temporarily unavailable. Connection reports the
            # actionable error later instead of silently dropping the device from the UI.
            return baseline


def _descriptor_from_lockdown(
    identifier: str,
    connection_type: str,
    info: dict[str, object],
) -> DeviceDescriptor:
    return DeviceDescriptor(
        identifier=identifier,
        name=_optional_string(info.get("DeviceName")),
        product_type=_optional_string(info.get("ProductType")),
        ios_version=_optional_string(info.get("ProductVersion")),
        connection=_connection_kind(connection_type),
    )


def _connection_kind(connection_type: str) -> ConnectionKind:
    normalized = connection_type.casefold()
    if normalized == "usb":
        return ConnectionKind.USB
    if normalized == "network":
        return ConnectionKind.NETWORK
    return ConnectionKind.UNKNOWN


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _require_modern_ios(descriptor: DeviceDescriptor) -> None:
    if descriptor.ios_version is None:
        raise GeoPortError(
            ErrorCode.DEVICE_METADATA_FAILED,
            "Could not determine the selected device's iOS version.",
            retryable=True,
        )

    version = _parse_ios_version(descriptor.ios_version)
    if version < _MIN_MODERN_IOS:
        raise GeoPortError(
            ErrorCode.IOS_VERSION_UNSUPPORTED,
            "This modernization path currently supports iOS 17.4 and newer.",
            retryable=False,
        )


def _parse_ios_version(value: str) -> tuple[int, int]:
    pieces = value.split(".")
    try:
        major = int(pieces[0])
        minor = int(pieces[1]) if len(pieces) > 1 else 0
    except (ValueError, IndexError) as exc:
        raise GeoPortError(
            ErrorCode.DEVICE_METADATA_FAILED,
            "The selected device reported an unrecognized iOS version.",
            retryable=True,
            cause=exc,
        ) from exc
    return major, minor


def _translate_exception(exc: BaseException, *, operation: str) -> GeoPortError:
    if isinstance(exc, GeoPortError):
        return exc

    if isinstance(
        exc,
        (
            NotTrustedError,
            NotPairedError,
            PairingDialogResponsePendingError,
            UserDeniedPairingError,
        ),
    ):
        return GeoPortError(
            ErrorCode.DEVICE_NOT_TRUSTED,
            "Unlock the iOS device, confirm Trust if prompted, then try again.",
            retryable=True,
            cause=exc,
        )

    if isinstance(exc, DeveloperModeIsNotEnabledError):
        return GeoPortError(
            ErrorCode.DEVELOPER_MODE_REQUIRED,
            "Developer Mode must be enabled on the selected iOS device.",
            retryable=True,
            cause=exc,
        )

    if isinstance(exc, DeviceVersionNotSupportedError):
        return GeoPortError(
            ErrorCode.IOS_VERSION_UNSUPPORTED,
            "The selected iOS version is not supported by the current device integration.",
            retryable=False,
            cause=exc,
        )

    if isinstance(
        exc,
        (DeviceNotFoundError, NoDeviceConnectedError, ConnectionTerminatedError, NotConnectedError),
    ):
        return GeoPortError(
            ErrorCode.DEVICE_DISCONNECTED,
            "The selected iOS device disconnected or is no longer reachable.",
            retryable=True,
            cause=exc,
        )

    if isinstance(
        exc,
        (
            UserspaceTunnelUnavailableError,
            TunneldConnectionError,
            RSDRequiredError,
            MuxException,
        ),
    ):
        return GeoPortError(
            ErrorCode.TUNNEL_UNAVAILABLE,
            "Could not establish the iOS developer-service connection.",
            retryable=True,
            cause=exc,
        )

    dependency_failure = isinstance(exc, (DvtException, PyMobileDevice3Exception, OSError))
    if operation == "set" and dependency_failure:
        return GeoPortError(
            ErrorCode.LOCATION_SET_FAILED,
            "The device rejected or lost the location-simulation request.",
            retryable=True,
            cause=exc,
        )

    if operation == "clear" and dependency_failure:
        return GeoPortError(
            ErrorCode.LOCATION_CLEAR_FAILED,
            "The simulated location could not be cleared through the active device session.",
            retryable=True,
            cause=exc,
        )

    if operation in {"connect", "discover", "disconnect"} and isinstance(
        exc, (InvalidServiceError, PyMobileDevice3Exception, OSError)
    ):
        code = (
            ErrorCode.TUNNEL_UNAVAILABLE
            if operation == "connect"
            else ErrorCode.DEVICE_DISCONNECTED
        )
        return GeoPortError(
            code,
            "The iOS device transport failed while GeoPortLocal was communicating with the device.",
            retryable=True,
            cause=exc,
        )

    return GeoPortError(
        ErrorCode.INTERNAL_ERROR,
        f"Unexpected device integration failure during {operation}.",
        retryable=False,
        cause=exc,
    )
