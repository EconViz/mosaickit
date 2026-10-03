"""Public exception hierarchy."""


class MosaicKitError(Exception):
    """Base error for core operations."""


class ConfigurationError(MosaicKitError, ValueError):
    """An invalid model or configuration value."""


class RenderError(MosaicKitError, RuntimeError):
    """A renderer cannot perform the requested operation."""


class BindingError(MosaicKitError, ValueError):
    """A parameter cannot be bound or evaluated."""


class LayoutWarning(UserWarning):
    """Automatic layout could not satisfy every placement constraint."""
