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
            "message": data
        }

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
            "message": f"[{severity.value}] {type(error).__name__}:{str(error)}"
        }

        if recovery_hint:
            response["recovery_hint"] = recovery_hint

        if context:
            response["error_context"] = context

        return ResponseBuilder._round_floats(response)
