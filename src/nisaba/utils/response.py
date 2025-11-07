"""Standardized response builders."""

from typing import Any, Dict, List, Optional
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ResponseBuilder:
    """Utility for building standardized responses."""

    @staticmethod
    def _round_floats(obj: Any, decimals: int = 2) -> Any:
        """
        Recursively round all float values in a data structure.

        Args:
            obj: Data structure to process (dict, list, tuple, or primitive)
            decimals: Number of decimal places (default 2)

        Returns:
            Data structure with all floats rounded
        """
        if isinstance(obj, float):
            return round(obj, decimals)
        elif isinstance(obj, dict):
            return {k: ResponseBuilder._round_floats(v, decimals) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ResponseBuilder._round_floats(item, decimals) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(ResponseBuilder._round_floats(item, decimals) for item in obj)
        else:
            return obj

    @staticmethod
    def success(
        data: Any,
        warnings: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build success response.

        Args:
            data: Response payload
            warnings: Optional warning messages
            metadata: Optional metadata

        Returns:
            Standardized success response
        """
        response = {
            "success": True,
            "data": data
        }

        if warnings:
            response["warnings"] = warnings

        if metadata:
            response["metadata"] = metadata

        return ResponseBuilder._round_floats(response)

    @staticmethod
    def error(
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recovery_hint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build error response.

        Args:
            error: Exception that occurred
            severity: Error severity level
            recovery_hint: Suggested recovery action
            context: Error context information

        Returns:
            Standardized error response
        """
        response = {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "severity": severity.value
        }

        if recovery_hint:
            response["recovery_hint"] = recovery_hint

        if context:
            response["error_context"] = context

        return ResponseBuilder._round_floats(response)

    @staticmethod
    def partial_success(
        data: Any,
        errors: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build response for operations that partially succeeded.

        Use when an operation completes but with some failures (e.g., batch operations
        where some items succeed and others fail).

        Args:
            data: Data for successful portion
            errors: List of error messages for failed portion
            execution_time_ms: Execution time in milliseconds
            metadata: Optional metadata (e.g., success_count, failure_count)

        Returns:
            Partial success response dictionary
        """
        response = {
            "success": True,
            "partial": True,
            "data": data,
            "errors": errors
        }

        if metadata:
            response["metadata"] = metadata

        return ResponseBuilder._round_floats(response)
