"""
MCP server discovery registry.

Manages .nisaba/mcp_servers.json for server registration and discovery.
Thread-safe registry for tracking running MCP server instances.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import fcntl

logger = logging.getLogger(__name__)


class MCPServerRegistry:
    """
    Thread-safe registry for MCP server instances.

    Manages .nisaba/mcp_servers.json in project root for server discovery.
    Automatically cleans up stale entries (dead processes).
    """

    REGISTRY_VERSION = "1.0"

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize registry.

        Args:
            registry_path: Path to registry JSON file.
                          Defaults to .nisaba/mcp_servers.json in cwd.
        """
        if registry_path is None:
            registry_path = Path.cwd() / ".nisaba" / "mcp_servers.json"

        self.registry_path = Path(registry_path)
        logger.debug(f"MCPServerRegistry initialized: {self.registry_path}")

    def register_server(self, server_id: str, server_info: dict) -> None:
        """
        Register or update a server entry.

        Atomically updates registry file with new server information.
        Cleans up stale entries before writing.

        Args:
            server_id: Unique server identifier (e.g., "nabu_12345")
            server_info: Server metadata dict with keys:
                - name: Server name
                - pid: Process ID
                - stdio_active: Whether STDIO transport is active
                - http: HTTP transport info (enabled, host, port, url)
                - started_at: ISO timestamp
                - cwd: Working directory
        """
        try:
            # Ensure parent directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)

            # Read current registry (or create new)
            data = self._read_registry()

            # Cleanup stale entries
            data["servers"] = self._cleanup_stale_entries(data.get("servers", {}))

            # Add/update this server
            data["servers"][server_id] = server_info

            # Write atomically
            self._write_registry(data)

            logger.info(f"Registered server: {server_id}")

        except Exception as e:
            logger.error(f"Failed to register server {server_id}: {e}", exc_info=True)
            raise

    def unregister_server(self, server_id: str) -> None:
        """
        Remove a server entry from registry.

        Args:
            server_id: Server identifier to remove
        """
        try:
            if not self.registry_path.exists():
                logger.debug(f"Registry does not exist, nothing to unregister: {server_id}")
                return

            # Read current registry
            data = self._read_registry()

            # Remove server if exists
            if server_id in data.get("servers", {}):
                del data["servers"][server_id]
                self._write_registry(data)
                logger.info(f"Unregistered server: {server_id}")
            else:
                logger.debug(f"Server not in registry: {server_id}")

        except Exception as e:
            logger.error(f"Failed to unregister server {server_id}: {e}", exc_info=True)
            raise

    def list_servers(self) -> Dict[str, dict]:
        """
        List all active servers.

        Filters out entries for dead processes.

        Returns:
            Dict mapping server_id -> server_info for active servers
        """
        try:
            if not self.registry_path.exists():
                return {}

            data = self._read_registry()
            servers = data.get("servers", {})

            # Filter to only alive processes
            return self._cleanup_stale_entries(servers)

        except Exception as e:
            logger.error(f"Failed to list servers: {e}", exc_info=True)
            return {}

    def _is_process_alive(self, pid: int) -> bool:
        """
        Check if process with given PID is alive.

        Uses os.kill(pid, 0) which doesn't send a signal but checks existence.

        Args:
            pid: Process ID to check

        Returns:
            True if process exists, False otherwise
        """
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
        except Exception as e:
            logger.warning(f"Error checking PID {pid}: {e}")
            return False

    def _cleanup_stale_entries(self, servers: Dict[str, dict]) -> Dict[str, dict]:
        """
        Remove entries for dead processes.

        Args:
            servers: Dict of server_id -> server_info

        Returns:
            Filtered dict with only alive servers
        """
        alive = {}

        for server_id, info in servers.items():
            pid = info.get("pid")

            if pid is None:
                logger.warning(f"Server entry missing PID: {server_id}")
                continue

            if self._is_process_alive(pid):
                alive[server_id] = info
            else:
                logger.debug(f"Removing stale entry for dead process: {server_id} (PID {pid})")

        return alive

    def _read_registry(self) -> dict:
        """
        Read registry from file with error handling.

        Returns:
            Registry data dict with "version" and "servers" keys
        """
        if not self.registry_path.exists():
            return {
                "version": self.REGISTRY_VERSION,
                "servers": {}
            }

        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                # Use flock for read lock
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

                # Validate structure
                if not isinstance(data, dict):
                    logger.warning("Invalid registry format, resetting")
                    return {
                        "version": self.REGISTRY_VERSION,
                        "servers": {}
                    }

                # Ensure required keys
                if "servers" not in data:
                    data["servers"] = {}
                if "version" not in data:
                    data["version"] = self.REGISTRY_VERSION

                return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse registry JSON: {e}")
            return {
                "version": self.REGISTRY_VERSION,
                "servers": {}
            }
        except Exception as e:
            logger.error(f"Failed to read registry: {e}", exc_info=True)
            return {
                "version": self.REGISTRY_VERSION,
                "servers": {}
            }

    def _write_registry(self, data: dict) -> None:
        """
        Write registry to file atomically.

        Uses atomic write pattern (write to temp, then rename).

        Args:
            data: Registry data to write
        """
        # Ensure parent directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        temp_path = self.registry_path.with_suffix('.tmp')

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                # Use flock for write lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename
            temp_path.replace(self.registry_path)

            logger.debug(f"Registry written: {self.registry_path}")

        except Exception as e:
            # Cleanup temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise
