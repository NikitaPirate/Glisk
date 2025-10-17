"""Event recovery service for fetching missed mint events from blockchain history.

This module provides functions to:
1. Fetch BatchMinted events from blockchain using eth_getLogs
2. Store recovered events in database with duplicate handling
3. Track recovery progress via system_state table
"""

from datetime import datetime
from typing import Any

import structlog
from eth_utils.abi import event_signature_to_log_topic
from web3 import Web3
from web3.types import LogReceipt

from glisk.core.config import Settings
from glisk.models.mint_event import MintEvent
from glisk.models.token import Token, TokenStatus
from glisk.uow import UnitOfWork

logger = structlog.get_logger()


def fetch_mint_events(
    settings: Settings,
    from_block: int,
    to_block: int | str,
    batch_size: int = 1000,
) -> list[dict[str, Any]]:
    """Fetch BatchMinted events from blockchain using eth_getLogs.

    Args:
        settings: Application settings containing Alchemy API key and contract address
        from_block: Starting block number (inclusive)
        to_block: Ending block number (inclusive) or "latest"
        batch_size: Maximum number of blocks per request (default: 1000)

    Returns:
        List of decoded event dictionaries with fields:
        - minter: Address of the NFT minter
        - author: Address of the prompt author
        - start_token_id: First token ID in batch
        - quantity: Number of tokens minted
        - total_paid: Total payment in wei
        - tx_hash: Transaction hash
        - block_number: Block number
        - log_index: Log index within transaction
        - block_timestamp: Block timestamp (UTC)

    Raises:
        ConnectionError: If unable to connect to Alchemy RPC
        ValueError: If event signature calculation fails
    """
    logger.info(
        "fetch_mint_events.start",
        from_block=from_block,
        to_block=to_block,
        batch_size=batch_size,
        network=settings.network,
    )

    # Initialize Web3 with Alchemy HTTP provider
    network_url_mapping = {
        "BASE_SEPOLIA": f"https://base-sepolia.g.alchemy.com/v2/{settings.alchemy_api_key}",
        "BASE_MAINNET": f"https://base-mainnet.g.alchemy.com/v2/{settings.alchemy_api_key}",
    }

    if settings.network not in network_url_mapping:
        raise ValueError(f"Unsupported network: {settings.network}")

    alchemy_url = network_url_mapping[settings.network]
    w3 = Web3(Web3.HTTPProvider(alchemy_url))

    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to Alchemy RPC: {alchemy_url}")

    # Calculate BatchMinted event signature
    # event BatchMinted(address indexed minter, address indexed promptAuthor,
    #                   uint256 startTokenId, uint256 quantity, uint256 totalPaid)
    event_signature = "BatchMinted(address,address,uint256,uint256,uint256)"
    event_topic = event_signature_to_log_topic(event_signature)

    logger.debug(
        "fetch_mint_events.config",
        event_signature=event_signature,
        event_topic=event_topic.hex(),
        contract_address=settings.glisk_nft_contract_address,
    )

    # Fetch logs with pagination
    events = []
    current_block = from_block
    to_block_num = to_block if isinstance(to_block, int) else w3.eth.block_number

    while current_block <= to_block_num:
        chunk_end = min(current_block + batch_size - 1, to_block_num)

        logger.debug(
            "fetch_mint_events.eth_getLogs",
            from_block=hex(current_block),
            to_block=hex(chunk_end),
        )

        try:
            logs = w3.eth.get_logs(
                {
                    "fromBlock": current_block,
                    "toBlock": chunk_end,
                    "address": Web3.to_checksum_address(settings.glisk_nft_contract_address),
                    "topics": [event_topic],
                }
            )

            logger.debug("fetch_mint_events.logs_received", count=len(logs))

            # Decode each log
            for log in logs:
                decoded_event = _decode_batch_minted_event(w3, log)
                events.append(decoded_event)

        except Exception as e:
            logger.error(
                "fetch_mint_events.error",
                error=str(e),
                from_block=current_block,
                to_block=chunk_end,
            )
            raise

        current_block = chunk_end + 1

    logger.info("fetch_mint_events.complete", total_events=len(events))
    return events


def _decode_batch_minted_event(w3: Web3, log: LogReceipt) -> dict[str, Any]:
    """Decode BatchMinted event from raw log data.

    BatchMinted event structure:
    - topics[0]: Event signature (keccak256 of event declaration)
    - topics[1]: Indexed minter address (32 bytes)
    - topics[2]: Indexed promptAuthor address (32 bytes)
    - data: ABI-encoded (startTokenId, quantity, totalPaid) tuple

    Args:
        w3: Web3 instance for address checksumming
        log: Raw log receipt from eth_getLogs

    Returns:
        Decoded event dictionary
    """
    # Extract indexed parameters from topics
    minter = w3.to_checksum_address("0x" + log["topics"][1].hex()[-40:])
    author = w3.to_checksum_address("0x" + log["topics"][2].hex()[-40:])

    # Decode non-indexed parameters from data field
    # Data contains: uint256 startTokenId, uint256 quantity, uint256 totalPaid (96 bytes total)
    data_hex = log["data"].hex() if isinstance(log["data"], bytes) else log["data"]
    if data_hex.startswith("0x"):
        data_hex = data_hex[2:]

    start_token_id = int(data_hex[0:64], 16)
    quantity = int(data_hex[64:128], 16)
    total_paid = int(data_hex[128:192], 16)

    # Fetch block timestamp
    block = w3.eth.get_block(log["blockNumber"])
    timestamp = block.get("timestamp", 0)  # type: ignore[arg-type]
    block_timestamp = datetime.utcfromtimestamp(timestamp)

    return {
        "minter": minter,
        "author": author,
        "start_token_id": start_token_id,
        "quantity": quantity,
        "total_paid": total_paid,
        "tx_hash": log["transactionHash"].hex()
        if isinstance(log["transactionHash"], bytes)
        else log["transactionHash"],
        "block_number": log["blockNumber"],
        "log_index": log["logIndex"],
        "block_timestamp": block_timestamp,
    }


async def store_recovered_events(
    events: list[dict[str, Any]],
    uow: UnitOfWork,
    settings: Settings,
) -> tuple[int, int]:
    """Store recovered events in database with duplicate handling.

    For each event:
    1. Lookup author by wallet address
    2. Create MintEvent record (skip if duplicate via UNIQUE constraint)
    3. Create Token record for each token in batch (skip if duplicate via PK constraint)

    Args:
        events: List of decoded event dictionaries from fetch_mint_events()
        uow: Unit of work for database transaction management
        settings: Application settings containing default author wallet

    Returns:
        Tuple of (stored_count, skipped_count)
    """
    stored_count = 0
    skipped_count = 0

    for event in events:
        # Lookup author (with fallback to default)
        author = await uow.authors.get_by_wallet(event["author"])
        if author is None:
            # Use default author as fallback
            author = await uow.authors.get_by_wallet(settings.glisk_default_author_wallet)

        # Skip if no author found (shouldn't happen with fallback, but be safe)
        if author is None:
            logger.warning(
                "store_recovered_events.no_author",
                author_wallet=event["author"],
                default_wallet=settings.glisk_default_author_wallet,
            )
            continue

        # Expand batch into individual token events
        for i in range(event["quantity"]):
            token_id = event["start_token_id"] + i

            try:
                # Create MintEvent record
                mint_event = MintEvent(
                    tx_hash=event["tx_hash"],
                    log_index=event["log_index"],
                    block_number=event["block_number"],
                    block_timestamp=event["block_timestamp"],
                    token_id=token_id,
                    author_wallet=event["author"],
                    recipient=event["minter"],
                    detected_at=datetime.utcnow(),
                )
                await uow.mint_events.add(mint_event)

                # Create Token record
                token = Token(
                    token_id=token_id,
                    minter_address=event["minter"],
                    author_id=author.id,
                    status=TokenStatus.DETECTED,
                    mint_timestamp=event["block_timestamp"],
                )
                await uow.tokens.add(token)

                stored_count += 1
                logger.debug(
                    "store_recovered_events.stored",
                    tx_hash=event["tx_hash"],
                    token_id=token_id,
                )

            except Exception as e:
                # Handle duplicate events gracefully (UNIQUE/PK constraint violations)
                error_str = str(e).lower()
                if (
                    "unique constraint" in error_str
                    or "duplicate key" in error_str
                    or "violates unique" in error_str
                ):
                    skipped_count += 1
                    logger.debug(
                        "store_recovered_events.duplicate",
                        tx_hash=event["tx_hash"],
                        token_id=token_id,
                    )
                else:
                    # Re-raise unexpected errors
                    logger.error(
                        "store_recovered_events.error",
                        error=str(e),
                        tx_hash=event["tx_hash"],
                        token_id=token_id,
                    )
                    raise

    logger.info(
        "store_recovered_events.complete",
        stored=stored_count,
        skipped=skipped_count,
    )

    return stored_count, skipped_count


async def update_last_processed_block(block_number: int, uow: UnitOfWork) -> None:
    """Update last processed block in system_state table.

    Args:
        block_number: Block number to store
        uow: Unit of work for database transaction
    """
    await uow.system_state.set_state("last_processed_block", block_number)
    logger.debug("update_last_processed_block", block_number=block_number)


async def get_last_processed_block(uow: UnitOfWork) -> int | None:
    """Get last processed block from system_state table.

    Args:
        uow: Unit of work for database query

    Returns:
        Last processed block number, or None if not set
    """
    value = await uow.system_state.get_state("last_processed_block")

    if value is None:
        return None

    return int(value)
