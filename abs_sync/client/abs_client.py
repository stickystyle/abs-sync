"""Base Audiobookshelf API client."""

import logging
from typing import Any, Optional

import json

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

logger = logging.getLogger("abs_sync")


class ABSClient:
    """Base client for Audiobookshelf API."""

    DEFAULT_TIMEOUT = 30

    def __init__(self, server_url: str, api_key: str):
        """
        Initialize the client.

        Args:
            server_url: Base URL of the ABS server
            api_key: API key for authentication
        """
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def _get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Optional[dict[str, Any]]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint (e.g., "/api/items/123")
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response or None on error
        """
        url = f"{self.server_url}{endpoint}"
        try:
            response = self._session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}")
            return None
        except ConnectionError:
            logger.error(f"Connection failed to {self.server_url}")
            return None
        except Timeout:
            logger.error(f"Request timed out: {url}")
            return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def _post(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Optional[dict[str, Any]]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint
            data: JSON body data
            timeout: Request timeout in seconds

        Returns:
            JSON response or None on error
        """
        url = f"{self.server_url}{endpoint}"
        try:
            response = self._session.post(url, json=data, timeout=timeout)
            response.raise_for_status()
            # Some endpoints return empty body on success
            if response.content:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # Some endpoints return non-JSON (e.g., "Scan started")
                    logger.debug(f"Non-JSON response from POST {endpoint}: {response.text[:100]}")
                    return {"success": True, "message": response.text}
            return {"success": True}
        except HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for POST {url}")
            if e.response.content:
                logger.debug(f"Response body: {e.response.text}")
            return None
        except ConnectionError:
            logger.error(f"Connection failed to {self.server_url}")
            return None
        except Timeout:
            logger.error(f"Request timed out: POST {url}")
            return None
        except Exception as e:
            logger.error(f"POST request failed: {e}")
            return None

    def _patch(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Optional[dict[str, Any]]:
        """
        Make a PATCH request.

        Args:
            endpoint: API endpoint
            data: JSON body data
            timeout: Request timeout in seconds

        Returns:
            JSON response or None on error
        """
        url = f"{self.server_url}{endpoint}"
        try:
            response = self._session.patch(url, json=data, timeout=timeout)
            response.raise_for_status()
            if response.content:
                return response.json()
            return {"success": True}
        except HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for PATCH {url}")
            return None
        except ConnectionError:
            logger.error(f"Connection failed to {self.server_url}")
            return None
        except Timeout:
            logger.error(f"Request timed out: PATCH {url}")
            return None
        except Exception as e:
            logger.error(f"PATCH request failed: {e}")
            return None

    def _delete(
        self,
        endpoint: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Make a DELETE request.

        Args:
            endpoint: API endpoint
            timeout: Request timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.server_url}{endpoint}"
        try:
            response = self._session.delete(url, timeout=timeout)
            response.raise_for_status()
            return True
        except HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for DELETE {url}")
            return False
        except Exception as e:
            logger.error(f"DELETE request failed: {e}")
            return False

    def ping(self) -> bool:
        """
        Check if the server is reachable and authenticated.

        Returns:
            True if server responds successfully
        """
        result = self._get("/api/me")
        return result is not None
