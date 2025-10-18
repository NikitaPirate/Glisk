"""Contract ABI utilities for GLISK backend.

This module provides utilities for loading smart contract ABIs from package resources.
ABIs are stored as JSON files in this directory and loaded dynamically at runtime.
"""

import json
from pathlib import Path


def get_contract_abi(contract_name: str = "GliskNFT") -> list[dict]:
    """Load contract ABI from package resources.

    ABIs are stored in backend/src/glisk/abi/ directory and are synced from
    Foundry build output using the sync-abi.sh script in the repository root.

    Args:
        contract_name: Name of the contract (default: "GliskNFT")

    Returns:
        ABI as list of function/event descriptors

    Raises:
        FileNotFoundError: If ABI file doesn't exist for the specified contract

    Example:
        >>> abi = get_contract_abi()
        >>> contract = w3.eth.contract(address=addr, abi=abi)
    """
    abi_path = Path(__file__).parent / f"{contract_name}.json"

    if not abi_path.exists():
        raise FileNotFoundError(
            f"ABI file not found: {abi_path}\n"
            f"Run './sync-abi.sh' from repository root to sync contract ABIs."
        )

    with open(abi_path) as f:
        return json.load(f)
