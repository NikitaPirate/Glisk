"""Pinata IPFS client for uploading images and metadata."""

import json
from typing import Any

import httpx

from glisk.services.exceptions import (
    IPFSAuthError,
    IPFSNetworkError,
    IPFSRateLimitError,
    IPFSValidationError,
    TransientError,
)


class PinataClient:
    """IPFS upload client using Pinata pinning service."""

    def __init__(self, jwt_token: str, gateway_domain: str = "gateway.pinata.cloud"):
        """Initialize Pinata client.

        Args:
            jwt_token: Pinata API JWT token (from PINATA_JWT env var)
            gateway_domain: Gateway domain for URL generation (default: public gateway)
        """
        self.jwt_token = jwt_token
        self.gateway_domain = gateway_domain
        self.base_url = "https://api.pinata.cloud"
        self.headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }

    async def upload_image(self, image_url: str, token_id: int) -> str:
        """Download image from URL and upload to IPFS via Pinata.

        Args:
            image_url: HTTP/HTTPS URL of image to upload (e.g., Replicate CDN URL)
            token_id: Token ID for semantic filename (e.g., s0-token-123.png)

        Returns:
            IPFS CID (Content Identifier) as string (CIDv1 format, e.g., "bafkrei...")

        Raises:
            TransientError: Network timeout, rate limit (429), service unavailable (503)
            PermanentError: Invalid API key (401), forbidden (403), bad request (400)
        """
        try:
            # Download image from URL
            async with httpx.AsyncClient(timeout=30.0) as client:
                image_response = await client.get(image_url)
                image_response.raise_for_status()
                image_data = image_response.content

            # Upload to Pinata with semantic filename
            filename = f"s0-token-{token_id}.png"
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"file": (filename, image_data, "image/png")}
                headers_copy = self.headers.copy()
                # Remove Content-Type for multipart upload
                del headers_copy["Content-Type"]

                # Prepare metadata for Pinata dashboard organization
                pinata_metadata = {
                    "name": filename,
                    "keyvalues": {"season": "0", "token_id": str(token_id)},
                }

                response = await client.post(
                    f"{self.base_url}/pinning/pinFileToIPFS",
                    headers=headers_copy,
                    files=files,
                    data={
                        "pinataOptions": '{"cidVersion": 1}',
                        "pinataMetadata": json.dumps(pinata_metadata),
                    },
                )

                # Error classification
                if response.status_code == 429:
                    raise IPFSRateLimitError(f"Rate limit exceeded: {response.text}")
                elif response.status_code in (500, 503):
                    raise TransientError(
                        f"Service unavailable ({response.status_code}): {response.text}"
                    )
                elif response.status_code == 401:
                    raise IPFSAuthError(
                        "Unauthorized: Invalid API key. "
                        "Check PINATA_JWT configuration in .env file. "
                        "Verify JWT token is active at https://app.pinata.cloud/developers/api-keys"
                    )
                elif response.status_code == 403:
                    raise IPFSAuthError(
                        "Forbidden: Access denied. "
                        "Check PINATA_JWT permissions (requires pinFileToIPFS access). "
                        "Verify account status and quota limits at https://app.pinata.cloud/billing"
                    )
                elif response.status_code == 400:
                    raise IPFSValidationError(f"Bad request: {response.text}")

                response.raise_for_status()
                result = response.json()
                return result["IpfsHash"]

        except httpx.TimeoutException as e:
            raise IPFSNetworkError(f"Request timeout after 30s: {str(e)}")
        except httpx.HTTPError as e:
            if isinstance(e, httpx.HTTPStatusError):
                # Already handled above
                raise
            raise IPFSNetworkError(f"Network error: {str(e)}")

    async def upload_metadata(self, metadata: dict[str, Any], token_id: int) -> str:
        """Upload metadata JSON to IPFS via Pinata.

        Args:
            metadata: ERC721 metadata dictionary with keys:
                - name (str): Token name
                - description (str): Token description
                - image (str): IPFS URI (ipfs://<CID>)
                - attributes (list, optional): Array of trait objects
            token_id: Token ID for semantic filename (e.g., s0-token-123-metadata.json)

        Returns:
            IPFS CID (Content Identifier) as string (CIDv1 format)

        Raises:
            TransientError: Network timeout, rate limit (429), service unavailable (503)
            PermanentError: Invalid API key (401), forbidden (403), bad request (400)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                metadata_filename = f"s0-token-{token_id}-metadata.json"
                payload = {
                    "pinataContent": metadata,
                    "pinataOptions": {"cidVersion": 1},
                    "pinataMetadata": {
                        "name": metadata_filename,
                        "keyvalues": {"season": "0", "token_id": str(token_id)},
                    },
                }

                response = await client.post(
                    f"{self.base_url}/pinning/pinJSONToIPFS",
                    headers=self.headers,
                    json=payload,
                )

                # Error classification (same as upload_image)
                if response.status_code == 429:
                    raise IPFSRateLimitError(f"Rate limit exceeded: {response.text}")
                elif response.status_code in (500, 503):
                    raise TransientError(
                        f"Service unavailable ({response.status_code}): {response.text}"
                    )
                elif response.status_code == 401:
                    raise IPFSAuthError(
                        "Unauthorized: Invalid API key. "
                        "Check PINATA_JWT configuration in .env file. "
                        "Verify JWT token is active at https://app.pinata.cloud/developers/api-keys"
                    )
                elif response.status_code == 403:
                    raise IPFSAuthError(
                        "Forbidden: Access denied. "
                        "Check PINATA_JWT permissions (requires pinJSONToIPFS access). "
                        "Verify account status and quota limits at https://app.pinata.cloud/billing"
                    )
                elif response.status_code == 400:
                    raise IPFSValidationError(f"Bad request: {response.text}")

                response.raise_for_status()
                result = response.json()
                return result["IpfsHash"]

        except httpx.TimeoutException as e:
            raise IPFSNetworkError(f"Request timeout after 30s: {str(e)}")
        except httpx.HTTPError as e:
            if isinstance(e, httpx.HTTPStatusError):
                # Already handled above
                raise
            raise IPFSNetworkError(f"Network error: {str(e)}")

    def get_gateway_url(self, cid: str) -> str:
        """Convert CID to gateway URL for browser access.

        Args:
            cid: IPFS CID

        Returns:
            Gateway URL (e.g., "https://gateway.pinata.cloud/ipfs/<CID>")
        """
        return f"https://{self.gateway_domain}/ipfs/{cid}"
