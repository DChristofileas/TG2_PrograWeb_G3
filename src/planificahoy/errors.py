"""Application exceptions without HTTP or provider-specific dependencies."""


class PlanificaHoyError(Exception):
    """Base class for expected application errors."""


class ConfigurationError(PlanificaHoyError):
    """The backend configuration is invalid."""


class InvalidInputError(PlanificaHoyError):
    """Input does not satisfy an application invariant."""


class UnsupportedActivityError(InvalidInputError):
    """The requested activity has no configured rules."""


class InvalidWeatherSnapshotError(PlanificaHoyError):
    """A weather snapshot cannot be evaluated safely."""


class ExternalServiceError(PlanificaHoyError):
    """Base class for failures while consulting an external provider."""


class ExternalServiceTimeoutError(ExternalServiceError):
    """The external provider did not respond before the timeout."""


class ExternalServiceConnectionError(ExternalServiceError):
    """The backend could not connect to the external provider."""


class ExternalServiceRequestError(ExternalServiceError):
    """The external provider rejected a request built by the adapter."""


class ExternalServiceRateLimitError(ExternalServiceError):
    """The external provider rate-limited the backend."""


class ExternalServiceUnavailableError(ExternalServiceError):
    """The external provider is temporarily unavailable."""


class ExternalResponseError(ExternalServiceError):
    """The external provider returned invalid or unexpected data."""
