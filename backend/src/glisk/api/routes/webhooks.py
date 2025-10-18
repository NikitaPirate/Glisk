"""Alchemy webhook endpoints for blockchain event processing.

This module implements webhook receivers for Alchemy blockchain event notifications,
specifically for GliskNFT BatchMinted events.
"""

import json
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from web3 import Web3

from glisk.api.dependencies import get_settings, get_uow_factory, validate_webhook_signature
from glisk.core.config import Settings
from glisk.models.mint_event import MintEvent
from glisk.models.token import Token, TokenStatus

logger = structlog.get_logger()
router = APIRouter()


def decode_batch_minted_event(log_data: dict, block_number: int) -> dict:
    """Decode BatchMinted event from Alchemy GraphQL webhook log.

    BatchMinted event structure:
        event BatchMinted(
            address indexed minter,       // topics[1]
            address indexed promptAuthor, // topics[2]
            uint256 indexed startTokenId, // topics[3]
            uint256 quantity,             // data[0:32]
            uint256 totalPaid             // data[32:64]
        );

    Args:
        log_data: Log entry from Alchemy GraphQL webhook payload
        block_number: Block number (from block.number field)

    Returns:
        Decoded event dictionary with keys:
            - minter: Minter's wallet address (checksummed)
            - prompt_author: Author's wallet address (checksummed)
            - start_token_id: First token ID in batch
            - quantity: Number of tokens minted
            - total_paid: Total payment in wei
            - tx_hash: Transaction hash
            - block_number: Block number
            - log_index: Log index within transaction

    Raises:
        ValueError: If log data is malformed or missing required fields
    """
    try:
        topics = log_data["topics"]
        data_hex = log_data["data"]

        # Parse indexed parameters from topics
        # topics[0] is event signature, topics[1-3] are indexed params
        if len(topics) < 4:
            raise ValueError(f"Invalid topics length: {len(topics)}, expected 4")

        # Extract addresses from topics (last 40 hex chars, add 0x prefix)
        minter = Web3.to_checksum_address("0x" + topics[1][-40:])
        prompt_author = Web3.to_checksum_address("0x" + topics[2][-40:])

        # Extract start_token_id from topics[3] (full 32 bytes as uint256)
        start_token_id = int(topics[3], 16)

        # Parse non-indexed parameters from data
        # Remove '0x' prefix and parse as hex
        data_bytes = data_hex[2:] if data_hex.startswith("0x") else data_hex

        # Each uint256 is 64 hex characters (32 bytes)
        if len(data_bytes) < 128:
            raise ValueError(f"Data too short: {len(data_bytes)} chars, expected at least 128")

        quantity = int(data_bytes[0:64], 16)
        total_paid = int(data_bytes[64:128], 16)

        # Extract transaction metadata from GraphQL structure
        # tx_hash is in log.transaction.hash
        transaction = log_data.get("transaction", {})
        tx_hash = transaction.get("hash", "")
        if not tx_hash:
            raise ValueError("Missing transaction.hash in log data")

        # log_index is in log.index (GraphQL returns int, not hex)
        log_index = log_data.get("index")
        if log_index is None:
            raise ValueError("Missing index in log data")

        return {
            "minter": minter,
            "prompt_author": prompt_author,
            "start_token_id": start_token_id,
            "quantity": quantity,
            "total_paid": total_paid,
            "tx_hash": tx_hash,
            "block_number": block_number,
            "log_index": log_index,
        }

    except (KeyError, IndexError, ValueError) as e:
        raise ValueError(f"Failed to decode BatchMinted event: {str(e)}") from e


@router.post("/alchemy")
async def receive_alchemy_webhook(
    raw_body: bytes = Depends(validate_webhook_signature),
    settings: Settings = Depends(get_settings),
    uow_factory=Depends(get_uow_factory),
):
    """Receive and process Alchemy webhook for NFT mint events.

    This endpoint:
    1. Validates HMAC signature (via dependency)
    2. Parses webhook payload for BatchMinted events
    3. Filters by contract address and transaction status
    4. Decodes event data (minter, author, token ID, etc.)
    5. Looks up author by wallet (or uses default)
    6. Creates MintEvent and Token records atomically
    7. Returns appropriate HTTP status codes

    Args:
        raw_body: Validated raw request body (from signature validation)
        settings: Application settings
        uow_factory: Unit of Work factory for database access

    Returns:
        JSON response with status and event details

    HTTP Status Codes:
        200: Event processed successfully
        400: Malformed payload or invalid event data
        409: Duplicate event (already processed)
        500: Internal server error (triggers Alchemy retry)
    """
    # Parse JSON payload
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as e:
        logger.error("webhook.invalid_json", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {str(e)}",
        )

    webhook_id = payload.get("webhookId", "unknown")
    event_id = payload.get("id", "unknown")

    logger.info(
        "webhook.received",
        webhook_id=webhook_id,
        event_id=event_id,
        event_type=payload.get("type"),
    )

    # DEBUG: Log full payload structure to understand Alchemy's format
    logger.info(
        "webhook.payload_debug",
        payload_keys=list(payload.keys()),
        full_payload=json.dumps(payload, indent=2)[:2000],  # First 2000 chars
    )

    # Extract block and logs from GraphQL payload
    try:
        block = payload["event"]["data"]["block"]
        logs = block["logs"]
        block_number = block.get("number")
        if block_number is None:
            raise ValueError("Missing block.number in payload")
    except (KeyError, ValueError) as e:
        logger.error(
            "webhook.malformed",
            missing_field=str(e),
            payload_structure=json.dumps(payload, indent=2)[:1000],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required field in payload: {str(e)}",
        )

    # Filter logs by contract address (GraphQL uses log.account.address)
    contract_address = settings.glisk_nft_contract_address.lower()
    matching_logs = [
        log for log in logs if log.get("account", {}).get("address", "").lower() == contract_address
    ]

    if not matching_logs:
        # No events for our contract - return 200 OK (not an error)
        logger.info(
            "webhook.no_matching_events",
            contract_address=contract_address,
            total_logs=len(logs),
        )
        return {"status": "success", "message": "No matching events for this contract"}

    logger.info(
        "webhook.matching_logs_found",
        count=len(matching_logs),
        contract_address=contract_address,
    )

    # Calculate BatchMinted event signature (with 0x prefix to match GraphQL format)
    event_signature = (
        "0x" + Web3.keccak(text="BatchMinted(address,address,uint256,uint256,uint256)").hex()
    )

    # Process each matching log
    processed_events = []
    for log_idx, log in enumerate(matching_logs):
        # Check if this is a BatchMinted event
        topics = log.get("topics", [])
        if not topics or topics[0] != event_signature:
            logger.info(
                "webhook.skip_non_batchminted",
                log_index=log_idx,
                topics_length=len(topics),
                expected_signature=event_signature,
                actual_signature=topics[0] if topics else None,
            )
            continue  # Skip non-BatchMinted events

        logger.info(
            "webhook.processing_batchminted",
            log_index=log_idx,
            tx_hash=log.get("transaction", {}).get("hash"),
        )

        # Check if transaction was successful (GraphQL: log.transaction.status)
        tx_status = log.get("transaction", {}).get("status")
        if tx_status != 1:
            tx_hash = log.get("transaction", {}).get("hash", "unknown")
            logger.warning("webhook.failed_transaction", tx_hash=tx_hash, tx_status=tx_status)
            continue  # Skip failed transactions

        # Check for chain reorg (may not be available in GraphQL response)
        if log.get("removed", False):
            tx_hash = log.get("transaction", {}).get("hash", "unknown")
            logger.warning("webhook.removed_log", tx_hash=tx_hash)
            continue  # Skip removed logs

        # Decode event (pass block_number from block level)
        try:
            event_data = decode_batch_minted_event(log, block_number)
            logger.info(
                "webhook.event_decoded",
                start_token_id=event_data["start_token_id"],
                quantity=event_data["quantity"],
                token_range=f"{event_data['start_token_id']}-\
                    {event_data['start_token_id'] + event_data['quantity'] - 1}",
                tx_hash=event_data["tx_hash"],
                minter=event_data["minter"],
            )
        except ValueError as e:
            logger.error("webhook.decode_error", error=str(e), log=log)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to decode event: {str(e)}",
            )

        # Store event and create token (atomic transaction)
        try:
            logger.info("webhook.checking_duplicate", tx_hash=event_data["tx_hash"])
            async with await uow_factory() as uow:
                # Check for duplicates
                event_exists = await uow.mint_events.exists(
                    tx_hash=event_data["tx_hash"],
                    log_index=event_data["log_index"],
                )

                if event_exists:
                    logger.warning(
                        "webhook.duplicate",
                        tx_hash=event_data["tx_hash"],
                        log_index=event_data["log_index"],
                    )
                    return {
                        "status": "duplicate",
                        "message": "Event already processed",
                        "tx_hash": event_data["tx_hash"],
                        "log_index": event_data["log_index"],
                    }

                logger.info("webhook.looking_up_author", author_wallet=event_data["prompt_author"])
                # Lookup author by wallet (case-insensitive)
                author = await uow.authors.get_by_wallet(event_data["prompt_author"])

                if not author:
                    logger.info(
                        "webhook.author_not_found_using_default",
                        author_wallet=event_data["prompt_author"],
                        default_wallet=settings.glisk_default_author_wallet,
                    )
                    # Use default author if not found
                    author = await uow.authors.get_by_wallet(settings.glisk_default_author_wallet)
                    if not author:
                        logger.error(
                            "webhook.default_author_not_found",
                            default_wallet=settings.glisk_default_author_wallet,
                        )
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Default author not configured",
                        )

                logger.info(
                    "webhook.creating_records",
                    start_token_id=event_data["start_token_id"],
                    quantity=event_data["quantity"],
                    author_id=author.id,
                )

                # Create MintEvent record (one per BatchMinted event)
                mint_event = MintEvent(
                    tx_hash=event_data["tx_hash"],
                    log_index=event_data["log_index"],
                    block_number=event_data["block_number"],
                    block_timestamp=datetime.utcnow(),  # Use current time as approximation
                    token_id=event_data["start_token_id"],  # Store start token ID as representative
                    author_wallet=event_data["prompt_author"],
                    recipient=event_data["minter"],
                    detected_at=datetime.utcnow(),
                )

                await uow.mint_events.add(mint_event)
                logger.info("webhook.mint_event_added", tx_hash=event_data["tx_hash"])

                # Create Token records for each token in batch
                created_token_ids = []
                for i in range(event_data["quantity"]):
                    token_id = event_data["start_token_id"] + i
                    token = Token(
                        token_id=token_id,
                        author_id=author.id,
                        status=TokenStatus.DETECTED,
                    )
                    await uow.tokens.add(token)
                    created_token_ids.append(token_id)

                logger.info(
                    "webhook.tokens_added",
                    count=len(created_token_ids),
                    token_ids=created_token_ids,
                )

                # Commit transaction (happens automatically on context exit)

            logger.info(
                "event.stored",
                tx_hash=event_data["tx_hash"],
                token_count=len(created_token_ids),
                token_ids=created_token_ids,
                author_wallet=event_data["prompt_author"],
                mint_event_id=str(mint_event.id),
            )

            processed_events.append(
                {
                    "mint_event_id": str(mint_event.id),
                    "token_count": len(created_token_ids),
                    "token_ids": created_token_ids,
                }
            )

        except Exception as e:
            logger.error(
                "webhook.storage_error",
                error=str(e),
                tx_hash=event_data.get("tx_hash"),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store event: {str(e)}",
            )

    logger.info("webhook.processing_complete", processed_count=len(processed_events))

    if not processed_events:
        logger.info("webhook.no_new_events")
        return {"status": "success", "message": "No new events to process"}

    logger.info("webhook.success", events_count=len(processed_events))
    return {
        "status": "success",
        "message": "Event processed successfully",
        "events": processed_events,
    }
