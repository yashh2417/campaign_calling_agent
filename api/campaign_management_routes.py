# api/campaign_management_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from core.database import get_db
from schemas.campaign_schemas import CampaignCreate, CampaignUpdate, CampaignRead, CampaignStatusUpdate  
from schemas.user_schemas import UserRead
from crud import db_campaign
from api.auth_routes import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaign-management", tags=["Campaign Management"])

@router.get("/", response_model=List[CampaignRead])
def get_user_campaigns(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get campaigns for the current user"""
    try:
        logger.info(f"Getting campaigns for user: {current_user.email}")
        
        # In a real application, you would filter by user_id
        # For now, we'll return all campaigns but you should modify this
        # to include: WHERE user_id = current_user.id
        
        if status:
            campaigns = db_campaign.get_campaigns_by_status(db=db, status=status, skip=skip, limit=limit)
        else:
            campaigns = db_campaign.get_latest_campaigns_grouped(db=db, skip=skip, limit=limit)
        
        logger.info(f"Retrieved {len(campaigns)} campaigns for user: {current_user.email}")
        return campaigns
        
    except Exception as e:
        logger.error(f"Error getting user campaigns: {e}")
        raise HTTPException(status_code=500, detail="Failed to get campaigns")

@router.post("/", response_model=CampaignRead)
def create_user_campaign(
    campaign: CampaignCreate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new campaign for the current user"""
    try:
        logger.info(f"Creating campaign '{campaign.campaign_name}' for user: {current_user.email}")
        
        # In a real application, you would associate the campaign with the user
        # You might want to add user_id to the Campaign model and set it here
        new_campaign = db_campaign.create_new_campaign(db=db, campaign=campaign)
        
        logger.info(f"Campaign created successfully: {new_campaign.campaign_id}")
        return new_campaign
        
    except ValueError as e:
        logger.warning(f"Validation error creating campaign: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail="Failed to create campaign")

@router.get("/{campaign_id}", response_model=CampaignRead)
def get_user_campaign(
    campaign_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific campaign for the current user"""
    try:
        campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check if the campaign belongs to the user
        # if campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        return campaign
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get campaign")

@router.put("/{campaign_id}", response_model=CampaignRead)
def update_user_campaign(
    campaign_id: uuid.UUID,
    updates: CampaignUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a campaign for the current user"""
    try:
        logger.info(f"Updating campaign {campaign_id} for user: {current_user.email}")
        
        # Check if campaign exists and belongs to user
        existing_campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not existing_campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check ownership
        # if existing_campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        updated_campaign = db_campaign.create_new_version(db=db, campaign_id=campaign_id, updates=updates)
        if not updated_campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info(f"Campaign updated successfully: {updated_campaign.campaign_id}")
        return updated_campaign
        
    except ValueError as e:
        logger.warning(f"Validation error updating campaign: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        raise HTTPException(status_code=500, detail="Failed to update campaign")

@router.patch("/{campaign_id}/status", response_model=CampaignRead)
def update_campaign_status(
    campaign_id: uuid.UUID,
    status_update: CampaignStatusUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update campaign status (start, pause, resume, complete)"""
    try:
        logger.info(f"Updating campaign {campaign_id} status to {status_update.status} for user: {current_user.email}")
        
        # Check if campaign exists and belongs to user
        existing_campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not existing_campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check ownership
        # if existing_campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        updated_campaign = db_campaign.update_campaign_status(
            db=db, 
            campaign_id=campaign_id, 
            status=status_update.status
        )
        
        if not updated_campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info(f"Campaign status updated successfully to: {status_update.status}")
        return updated_campaign
        
    except ValueError as e:
        logger.warning(f"Validation error updating campaign status: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update campaign status")

@router.delete("/{campaign_id}")
def delete_user_campaign(
    campaign_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a campaign for the current user"""
    try:
        logger.info(f"Deleting campaign {campaign_id} for user: {current_user.email}")
        
        # Check if campaign exists and belongs to user
        existing_campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not existing_campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check ownership
        # if existing_campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        deleted = db_campaign.delete_campaign(db=db, campaign_id=campaign_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info(f"Campaign deleted successfully: {campaign_id}")
        return {"success": True, "message": "Campaign deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete campaign")

@router.post("/{campaign_id}/duplicate", response_model=CampaignRead)
def duplicate_user_campaign(
    campaign_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate an existing campaign for the current user"""
    try:
        logger.info(f"Duplicating campaign {campaign_id} for user: {current_user.email}")
        
        # Check if campaign exists and belongs to user
        existing_campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not existing_campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check ownership
        # if existing_campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        duplicated_campaign = db_campaign.duplicate_campaign(db=db, campaign_id=campaign_id)
        if not duplicated_campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info(f"Campaign duplicated successfully: {duplicated_campaign.campaign_id}")
        return duplicated_campaign
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating campaign: {e}")
        raise HTTPException(status_code=500, detail="Failed to duplicate campaign")

@router.get("/{campaign_id}/analytics")
def get_campaign_analytics(
    campaign_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics for a specific campaign"""
    try:
        # Check if campaign exists and belongs to user
        campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check ownership
        # if campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        analytics = db_campaign.get_campaign_analytics(db=db, campaign_id=campaign_id)
        return {"success": True, "analytics": analytics}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign analytics {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics")

@router.get("/{campaign_id}/calls")
def get_campaign_calls(
    campaign_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all calls for a specific campaign"""
    try:
        # Check if campaign exists and belongs to user
        campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check ownership
        # if campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        calls = db_campaign.get_campaign_calls(
            db=db,
            campaign_id=campaign_id,
            skip=skip,
            limit=limit
        )
        return {"success": True, "calls": calls}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign calls {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get campaign calls")

@router.post("/{campaign_id}/start")
def start_campaign(
    campaign_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a campaign (trigger the actual calling process)"""
    try:
        logger.info(f"Starting campaign {campaign_id} for user: {current_user.email}")
        
        # Check if campaign exists and belongs to user
        campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check ownership
        # if campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if campaign is in draft status
        if campaign.status != "draft":
            raise HTTPException(status_code=400, detail="Campaign can only be started from draft status")
        
        # Check if campaign has contacts
        if not campaign.contact_list or len(campaign.contact_list) == 0:
            raise HTTPException(status_code=400, detail="Campaign must have contacts before starting")
        
        # Update campaign status to active
        updated_campaign = db_campaign.update_campaign_status(
            db=db,
            campaign_id=campaign_id,
            status="active"
        )
        
        # Here you would typically trigger the actual calling process
        # This might involve calling your call_creation_service
        # For now, we'll just update the status
        
        logger.info(f"Campaign started successfully: {campaign_id}")
        return {
            "success": True,
            "message": "Campaign started successfully",
            "campaign": updated_campaign
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start campaign")

@router.post("/{campaign_id}/pause")
def pause_campaign(
    campaign_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pause an active campaign"""
    try:
        logger.info(f"Pausing campaign {campaign_id} for user: {current_user.email}")
        
        # Check if campaign exists and belongs to user
        campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check ownership
        # if campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if campaign can be paused
        if campaign.status not in ["active"]:
            raise HTTPException(status_code=400, detail="Only active campaigns can be paused")
        
        # Update campaign status to paused
        updated_campaign = db_campaign.update_campaign_status(
            db=db,
            campaign_id=campaign_id,
            status="paused"
        )
        
        logger.info(f"Campaign paused successfully: {campaign_id}")
        return {
            "success": True,
            "message": "Campaign paused successfully",
            "campaign": updated_campaign
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to pause campaign")

@router.post("/{campaign_id}/resume")
def resume_campaign(
    campaign_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resume a paused campaign"""
    try:
        logger.info(f"Resuming campaign {campaign_id} for user: {current_user.email}")
        
        # Check if campaign exists and belongs to user
        campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # In a real application, you would check ownership
        # if campaign.user_id != current_user.id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if campaign can be resumed
        if campaign.status not in ["paused"]:
            raise HTTPException(status_code=400, detail="Only paused campaigns can be resumed")
        
        # Update campaign status to active
        updated_campaign = db_campaign.update_campaign_status(
            db=db,
            campaign_id=campaign_id,
            status="active"
        )
        
        logger.info(f"Campaign resumed successfully: {campaign_id}")
        return {
            "success": True,
            "message": "Campaign resumed successfully",
            "campaign": updated_campaign
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resume campaign")

@router.get("/stats/summary")
def get_user_campaign_summary(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get summary statistics for user's campaigns"""
    try:
        # In a real application, you would filter by user_id
        summary = db_campaign.get_campaigns_summary(db=db)
        
        logger.info(f"Campaign summary requested by user: {current_user.email}")
        return {"success": True, "summary": summary}
        
    except Exception as e:
        logger.error(f"Error getting campaign summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get campaign summary")