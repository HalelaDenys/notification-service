def get_error_cause(exc: Exception) -> str | None:
    """
    Identifies the root causes of exceptions
    :param exc: exception
    """
    if exc.__cause__ is None:
        return None
    return f"{type(exc.__cause__).__name__}: {exc.__cause__}"
