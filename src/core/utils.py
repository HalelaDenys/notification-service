from core.exceptions import NonRetryableError, RetryableError


def get_error_cause(error: Exception) -> str:
    """
    Build a string describing the error type, category, and cause.

    Format: '<error_type> -> <error_category> -> <cause_type>'.

    :param error: Exception to describe.
    :return: Formatted error classification string.
    """
    if isinstance(error, RetryableError):
        error_category = RetryableError.__name__
        cause_type = error.cause_type or "unknown"
    elif isinstance(error, NonRetryableError):
        error_category = NonRetryableError.__name__
        cause_type = error.cause_type or "unknown"
    else:
        error_category = type(error).__name__
        cause_type = "unknown"

    return f"{type(error).__name__} -> {error_category} -> {cause_type}"
