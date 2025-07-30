import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from schemas.campaign_schemas import CampaignCreate, CampaignUpdate, CampaignRead, CampaignStatusUpdate
from crud import db_campaign
from core.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

@router.post("/", response_model=CampaignRead)
def create_campaign(campaign: CampaignCreate, db: Session = Depends(get_db)):
    """Create a new campaign"""
    try:
        return db_campaign.create_new_campaign(db=db, campaign=campaign)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail="Failed to create campaign")

@router.get("/", response_model=List[CampaignRead])
def get_campaigns_dashboard(
    skip: int = 0, 
    limit: int = 50, 
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get campaigns for dashboard with optional filtering"""
    try:
        if status:
            return db_campaign.get_campaigns_by_status(db=db, status=status, skip=skip, limit=limit)
        return db_campaign.get_latest_campaigns_grouped(db=db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching campaigns: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch campaigns")

@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific campaign by ID"""
    campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.get("/{campaign_group_id}/history", response_model=List[CampaignRead])
def get_campaign_version_history(campaign_group_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get version history for a campaign group"""
    history = db_campaign.get_campaign_history(db=db, campaign_group_id=campaign_group_id)
    if not history:
        raise HTTPException(status_code=404, detail="Campaign history not found")
    return history

@router.put("/{campaign_id}", response_model=CampaignRead)
def update_campaign(campaign_id: uuid.UUID, updates: CampaignUpdate, db: Session = Depends(get_db)):
    """Update a campaign (creates new version)"""
    try:
        new_version = db_campaign.create_new_version(db=db, campaign_id=campaign_id, updates=updates)
        if not new_version:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return new_version
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update campaign")

@router.patch("/{campaign_id}/status", response_model=CampaignRead)
def update_campaign_status(
    campaign_id: uuid.UUID, 
    status_update: CampaignStatusUpdate, 
    db: Session = Depends(get_db)
):
    """Update campaign status (pause/resume/complete)"""
    try:
        campaign = db_campaign.update_campaign_status(
            db=db, 
            campaign_id=campaign_id, 
            status=status_update.status
        )
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating campaign status {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update campaign status")

@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a campaign (soft delete by marking as inactive)"""
    try:
        deleted = db_campaign.delete_campaign(db=db, campaign_id=campaign_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return {"success": True, "message": "Campaign deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete campaign")

@router.post("/{campaign_id}/duplicate", response_model=CampaignRead)
def duplicate_campaign(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    """Duplicate an existing campaign"""
    try:
        duplicated = db_campaign.duplicate_campaign(db=db, campaign_id=campaign_id)
        if not duplicated:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return duplicated
    except Exception as e:
        logger.error(f"Error duplicating campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to duplicate campaign")

@router.get("/{campaign_id}/analytics")
def get_campaign_analytics(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get analytics for a specific campaign"""
    try:
        # Check if campaign exists
        campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
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
    db: Session = Depends(get_db)
):
    """Get all calls for a specific campaign"""
    try:
        # Check if campaign exists
        campaign = db_campaign.get_campaign_by_id(db=db, campaign_id=campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
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

@router.get("/stats/summary")
def get_campaigns_summary(db: Session = Depends(get_db)):
    """Get summary statistics for all campaigns"""
    try:
        summary = db_campaign.get_campaigns_summary(db=db)
        return {"success": True, "summary": summary}
    except Exception as e:
        logger.error(f"Error getting campaigns summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get summary")