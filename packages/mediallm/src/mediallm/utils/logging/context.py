#!/usr/bin/env python3
# Author: Arun Brahma

import contextvars
from typing import Any
from typing import Final


class ContextConstants:
    """Constants for logging context management."""

    REQUEST_ID_KEY: Final[str] = "request_id"
    USER_ID_KEY: Final[str] = "user_id"
    TENANT_ID_KEY: Final[str] = "tenant_id"
    CUSTOM_CONTEXT_KEY: Final[str] = "custom_context"
    CUSTOM_PREFIX: Final[str] = "custom_"


class ContextVarRegistry:
    """Registry for context variables with centralized management."""

    def __init__(self) -> None:
        """Initialize context variable registry."""
        self._variables: dict[str, contextvars.ContextVar] = {
            ContextConstants.REQUEST_ID_KEY: contextvars.ContextVar(ContextConstants.REQUEST_ID_KEY, default=None),
            ContextConstants.USER_ID_KEY: contextvars.ContextVar(ContextConstants.USER_ID_KEY, default=None),
            ContextConstants.TENANT_ID_KEY: contextvars.ContextVar(ContextConstants.TENANT_ID_KEY, default=None),
            ContextConstants.CUSTOM_CONTEXT_KEY: contextvars.ContextVar(
                ContextConstants.CUSTOM_CONTEXT_KEY, default=None
            ),
        }

    def get_var(self, key: str) -> contextvars.ContextVar:
        """Get context variable by key."""
        if key not in self._variables:
            raise KeyError(f"Context variable '{key}' not registered")
        return self._variables[key]

    def get_value(self, key: str) -> Any:
        """Get current value of context variable."""
        return self.get_var(key).get()

    def set_value(self, key: str, value: Any) -> contextvars.Token:
        """Set value of context variable and return token."""
        return self.get_var(key).set(value)

    def reset_value(self, key: str, token: contextvars.Token) -> None:
        """Reset context variable using token."""
        self.get_var(key).reset(token)

    def clear_all(self) -> None:
        """Clear all context variables."""
        for var in self._variables.values():
            var.set(None)


# Global registry instance
_registry = ContextVarRegistry()


class LogContext:
    """Context manager for binding logging context."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize context with key-value pairs."""
        self.context_data = kwargs
        self._tokens: dict[str, contextvars.Token] = {}

    def __enter__(self) -> "LogContext":
        """Bind context variables."""
        for key, value in self.context_data.items():
            self._bind_context_variable(key, value)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Restore context variables."""
        self._restore_context_variables()

    def _bind_context_variable(self, key: str, value: Any) -> None:
        """Bind a single context variable."""
        if self._is_standard_context_key(key):
            self._bind_standard_context(key, value)
        else:
            self._bind_custom_context(key, value)

    def _is_standard_context_key(self, key: str) -> bool:
        """Check if key is a standard context variable."""
        return key in {
            ContextConstants.REQUEST_ID_KEY,
            ContextConstants.USER_ID_KEY,
            ContextConstants.TENANT_ID_KEY,
        }

    def _bind_standard_context(self, key: str, value: Any) -> None:
        """Bind standard context variable."""
        token = _registry.set_value(key, value)
        self._tokens[key] = token

    def _bind_custom_context(self, key: str, value: Any) -> None:
        """Bind custom context variable."""
        current_context = _registry.get_value(ContextConstants.CUSTOM_CONTEXT_KEY) or {}
        updated_context = current_context.copy()
        updated_context[key] = value

        token = _registry.set_value(ContextConstants.CUSTOM_CONTEXT_KEY, updated_context)
        self._tokens[f"{ContextConstants.CUSTOM_PREFIX}{key}"] = token

    def _restore_context_variables(self) -> None:
        """Restore all context variables using stored tokens."""
        for token_key, token in self._tokens.items():
            if token_key.startswith(ContextConstants.CUSTOM_PREFIX):
                _registry.reset_value(ContextConstants.CUSTOM_CONTEXT_KEY, token)
            else:
                _registry.reset_value(token_key, token)


def bind_context(**kwargs: Any) -> LogContext:
    """Create a context manager for binding logging context.

    Args:
        **kwargs: Context variables to bind

    Returns:
        LogContext instance that can be used as a context manager

    Example:
        with bind_context(request_id="req-123", user_id="user-456"):
            logger.info("Processing request")
    """
    return LogContext(**kwargs)


def clear_context() -> None:
    """Clear all context variables."""
    _registry.clear_all()


def get_context() -> dict[str, Any]:
    """Get current context data."""
    context = {}

    context.update(_get_standard_context())
    context.update(_get_custom_context())

    return context


def _get_standard_context() -> dict[str, Any]:
    """Get standard context variables."""
    context = {}

    for key in [
        ContextConstants.REQUEST_ID_KEY,
        ContextConstants.USER_ID_KEY,
        ContextConstants.TENANT_ID_KEY,
    ]:
        value = _registry.get_value(key)
        if value is not None:
            context[key] = value

    return context


def _get_custom_context() -> dict[str, Any]:
    """Get custom context variables."""
    custom_context = _registry.get_value(ContextConstants.CUSTOM_CONTEXT_KEY)
    return custom_context.copy() if custom_context else {}


def request_id(value: str) -> LogContext:
    """Create a context manager that binds request_id.

    Args:
        value: Request ID value

    Returns:
        LogContext instance

    Example:
        with request_id("req-123"):
            logger.info("Processing request")
    """
    return LogContext(request_id=value)


def user_id(value: str) -> LogContext:
    """Create a context manager that binds user_id.

    Args:
        value: User ID value

    Returns:
        LogContext instance

    Example:
        with user_id("user-456"):
            logger.info("User action")
    """
    return LogContext(user_id=value)


def tenant_id(value: str) -> LogContext:
    """Create a context manager that binds tenant_id.

    Args:
        value: Tenant ID value

    Returns:
        LogContext instance

    Example:
        with tenant_id("tenant-789"):
            logger.info("Tenant operation")
    """
    return LogContext(tenant_id=value)
