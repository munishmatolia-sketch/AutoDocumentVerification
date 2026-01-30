"""Webhooks router for the document forensics API."""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel, HttpUrl
from slowapi import Limiter
from slowapi.util import get_remote_address
import httpx

from ..auth import User, require_read, require_write, require_admin
from ..exceptions import WebhookError

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class WebhookConfig(BaseModel):
    """Webhook configuration model."""
    webhook_id: Optional[str] = None
    url: HttpUrl
    events: List[str]
    secret: Optional[str] = None
    active: bool = True
    description: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook response model."""
    webhook_id: str
    url: str
    events: List[str]
    active: bool
    description: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class WebhookListResponse(BaseModel):
    """Webhook list response model."""
    webhooks: List[WebhookResponse]
    total: int
    page: int
    page_size: int


class WebhookDelivery(BaseModel):
    """Webhook delivery model."""
    delivery_id: str
    webhook_id: str
    event: str
    payload: Dict[str, Any]
    status: str
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    delivered_at: str
    attempts: int = 1


class WebhookDeliveryListResponse(BaseModel):
    """Webhook delivery list response model."""
    deliveries: List[WebhookDelivery]
    total: int
    page: int
    page_size: int


# In-memory webhook storage (in production, use database)
webhooks_db: Dict[str, dict] = {}
deliveries_db: Dict[str, WebhookDelivery] = {}

# Supported webhook events
SUPPORTED_EVENTS = [
    "document.uploaded",
    "document.deleted",
    "analysis.started",
    "analysis.completed",
    "analysis.failed",
    "batch.started",
    "batch.completed",
    "batch.failed",
    "report.generated"
]


@router.post("/register", response_model=WebhookResponse)
async def register_webhook(
    webhook_config: WebhookConfig,
    current_user: User = Depends(require_admin)
):
    """
    Register a new webhook configuration (alias for create_webhook).
    
    Requires admin permissions.
    """
    return await create_webhook(webhook_config, current_user)


@router.post("/", response_model=WebhookResponse)
async def create_webhook(
    webhook_config: WebhookConfig,
    current_user: User = Depends(require_admin)
):
    """
    Create a new webhook configuration.
    
    Requires admin permissions.
    """
    try:
        # Validate events
        invalid_events = [event for event in webhook_config.events if event not in SUPPORTED_EVENTS]
        if invalid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported events: {invalid_events}. Supported events: {SUPPORTED_EVENTS}"
            )
        
        # Generate webhook ID
        webhook_id = str(uuid4())
        
        # Store webhook configuration
        from datetime import datetime
        webhook_data = {
            "webhook_id": webhook_id,
            "url": str(webhook_config.url),
            "events": webhook_config.events,
            "secret": webhook_config.secret,
            "active": webhook_config.active,
            "description": webhook_config.description,
            "created_by": current_user.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": None
        }
        
        webhooks_db[webhook_id] = webhook_data
        
        logger.info(f"Webhook created: {webhook_id} by user {current_user.user_id}")
        
        return WebhookResponse(
            webhook_id=webhook_id,
            url=webhook_data["url"],
            events=webhook_data["events"],
            active=webhook_data["active"],
            description=webhook_data["description"],
            created_at=webhook_data["created_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook creation failed: {str(e)}")
        raise WebhookError(f"Failed to create webhook: {str(e)}")


@router.get("/", response_model=WebhookListResponse)
async def list_webhooks(
    page: int = 1,
    page_size: int = 20,
    active_only: bool = False,
    current_user: User = Depends(require_admin)
):
    """
    List webhook configurations.
    
    Requires admin permissions.
    """
    try:
        all_webhooks = list(webhooks_db.values())
        
        # Filter active webhooks if requested
        if active_only:
            all_webhooks = [wh for wh in all_webhooks if wh["active"]]
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_webhooks = all_webhooks[start_idx:end_idx]
        
        # Convert to response format
        webhook_responses = [
            WebhookResponse(
                webhook_id=wh["webhook_id"],
                url=wh["url"],
                events=wh["events"],
                active=wh["active"],
                description=wh["description"],
                created_at=wh["created_at"],
                updated_at=wh["updated_at"]
            )
            for wh in paginated_webhooks
        ]
        
        logger.info(f"Listed {len(webhook_responses)} webhooks for user {current_user.user_id}")
        
        return WebhookListResponse(
            webhooks=webhook_responses,
            total=len(all_webhooks),
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        logger.error(f"Error listing webhooks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list webhooks: {str(e)}"
        )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    current_user: User = Depends(require_admin)
):
    """
    Get webhook configuration by ID.
    
    Requires admin permissions.
    """
    try:
        webhook_data = webhooks_db.get(webhook_id)
        if not webhook_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        return WebhookResponse(
            webhook_id=webhook_data["webhook_id"],
            url=webhook_data["url"],
            events=webhook_data["events"],
            active=webhook_data["active"],
            description=webhook_data["description"],
            created_at=webhook_data["created_at"],
            updated_at=webhook_data["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook {webhook_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webhook: {str(e)}"
        )


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    webhook_config: WebhookConfig,
    current_user: User = Depends(require_admin)
):
    """
    Update webhook configuration.
    
    Requires admin permissions.
    """
    try:
        webhook_data = webhooks_db.get(webhook_id)
        if not webhook_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        # Validate events
        invalid_events = [event for event in webhook_config.events if event not in SUPPORTED_EVENTS]
        if invalid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported events: {invalid_events}. Supported events: {SUPPORTED_EVENTS}"
            )
        
        # Update webhook data
        from datetime import datetime
        webhook_data.update({
            "url": str(webhook_config.url),
            "events": webhook_config.events,
            "secret": webhook_config.secret,
            "active": webhook_config.active,
            "description": webhook_config.description,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Webhook updated: {webhook_id} by user {current_user.user_id}")
        
        return WebhookResponse(
            webhook_id=webhook_data["webhook_id"],
            url=webhook_data["url"],
            events=webhook_data["events"],
            active=webhook_data["active"],
            description=webhook_data["description"],
            created_at=webhook_data["created_at"],
            updated_at=webhook_data["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook update failed for {webhook_id}: {str(e)}")
        raise WebhookError(f"Failed to update webhook: {str(e)}")


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(require_admin)
):
    """
    Delete webhook configuration.
    
    Requires admin permissions.
    """
    try:
        if webhook_id not in webhooks_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        del webhooks_db[webhook_id]
        
        logger.info(f"Webhook deleted: {webhook_id} by user {current_user.user_id}")
        
        return {"message": f"Webhook {webhook_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook deletion failed for {webhook_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete webhook: {str(e)}"
        )


@router.post("/{webhook_id}/test")
@limiter.limit("5/minute")
async def test_webhook(
    request: Request,
    webhook_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Test webhook by sending a test event.
    
    Rate limited to 5 tests per minute per IP address.
    Requires admin permissions.
    """
    try:
        webhook_data = webhooks_db.get(webhook_id)
        if not webhook_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        if not webhook_data["active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot test inactive webhook"
            )
        
        # Create test payload
        test_payload = {
            "event": "webhook.test",
            "timestamp": "2024-01-01T00:00:00Z",
            "data": {
                "webhook_id": webhook_id,
                "message": "This is a test webhook delivery",
                "test": True
            }
        }
        
        # Send webhook in background
        background_tasks.add_task(
            send_webhook,
            webhook_data["url"],
            test_payload,
            webhook_data.get("secret"),
            webhook_id,
            "webhook.test"
        )
        
        logger.info(f"Test webhook sent for {webhook_id} by user {current_user.user_id}")
        
        return {"message": f"Test webhook sent to {webhook_data['url']}"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook test failed for {webhook_id}: {str(e)}")
        raise WebhookError(f"Failed to test webhook: {str(e)}")


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def list_webhook_deliveries(
    webhook_id: str,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    """
    List webhook delivery attempts.
    
    Requires admin permissions.
    """
    try:
        webhook_data = webhooks_db.get(webhook_id)
        if not webhook_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        # Filter deliveries for this webhook
        webhook_deliveries = [
            delivery for delivery in deliveries_db.values()
            if delivery.webhook_id == webhook_id
        ]
        
        # Apply status filter
        if status_filter:
            webhook_deliveries = [
                delivery for delivery in webhook_deliveries
                if delivery.status == status_filter
            ]
        
        # Sort by delivery time (most recent first)
        webhook_deliveries.sort(key=lambda x: x.delivered_at, reverse=True)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_deliveries = webhook_deliveries[start_idx:end_idx]
        
        logger.info(f"Listed {len(paginated_deliveries)} webhook deliveries for {webhook_id}")
        
        return WebhookDeliveryListResponse(
            deliveries=paginated_deliveries,
            total=len(webhook_deliveries),
            page=page,
            page_size=page_size
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing webhook deliveries for {webhook_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list webhook deliveries: {str(e)}"
        )


@router.get("/events")
async def list_supported_events(
    current_user: User = Depends(require_read)
):
    """
    List supported webhook events.
    
    Requires read permissions.
    """
    return {
        "supported_events": SUPPORTED_EVENTS,
        "event_descriptions": {
            "document.uploaded": "Triggered when a document is successfully uploaded",
            "document.deleted": "Triggered when a document is deleted",
            "analysis.started": "Triggered when document analysis begins",
            "analysis.completed": "Triggered when document analysis completes successfully",
            "analysis.failed": "Triggered when document analysis fails",
            "batch.started": "Triggered when batch processing begins",
            "batch.completed": "Triggered when batch processing completes",
            "batch.failed": "Triggered when batch processing fails",
            "report.generated": "Triggered when a report is generated"
        }
    }


async def send_webhook(
    url: str,
    payload: Dict[str, Any],
    secret: Optional[str],
    webhook_id: str,
    event: str,
    max_retries: int = 3
):
    """
    Send webhook payload to configured URL with retry logic.
    """
    delivery_id = str(uuid4())
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "DocumentForensics-Webhook/1.0",
        "X-Webhook-ID": webhook_id,
        "X-Delivery-ID": delivery_id
    }
    
    # Add signature if secret is provided
    if secret:
        import hmac
        import hashlib
        import json
        
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"
    
    delivery = WebhookDelivery(
        delivery_id=delivery_id,
        webhook_id=webhook_id,
        event=event,
        payload=payload,
        status="pending",
        delivered_at="",
        attempts=0
    )
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_retries):
            try:
                delivery.attempts = attempt + 1
                
                response = await client.post(url, json=payload, headers=headers)
                
                from datetime import datetime
                delivery.delivered_at = datetime.utcnow().isoformat()
                delivery.response_code = response.status_code
                delivery.response_body = response.text[:1000]  # Limit response body size
                
                if response.status_code < 400:
                    delivery.status = "success"
                    logger.info(f"Webhook delivered successfully: {delivery_id}")
                    break
                else:
                    delivery.status = "failed"
                    logger.warning(f"Webhook delivery failed with status {response.status_code}: {delivery_id}")
                    
            except Exception as e:
                delivery.status = "failed"
                delivery.response_body = str(e)[:1000]
                logger.error(f"Webhook delivery error (attempt {attempt + 1}): {str(e)}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
    
    # Store delivery record
    deliveries_db[delivery_id] = delivery


async def trigger_webhook_event(event: str, data: Dict[str, Any]):
    """
    Trigger webhook event for all configured webhooks.
    """
    try:
        active_webhooks = [
            wh for wh in webhooks_db.values()
            if wh["active"] and event in wh["events"]
        ]
        
        if not active_webhooks:
            return
        
        from datetime import datetime
        payload = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Send webhooks concurrently
        tasks = []
        for webhook in active_webhooks:
            task = send_webhook(
                webhook["url"],
                payload,
                webhook.get("secret"),
                webhook["webhook_id"],
                event
            )
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Triggered {len(tasks)} webhooks for event: {event}")
    
    except Exception as e:
        logger.error(f"Error triggering webhook event {event}: {str(e)}")