import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.campaign import Campaign
from schemas.campaign_schemas import CampaignCreate, CampaignUpdate

def get_latest_campaigns_grouped(db: Session, skip: int = 0, limit: int = 50):
    """Get the latest version of each campaign group with pagination"""
    latest_version_subquery = db.query(
        Campaign.campaign_group_id,
        func.max(Campaign.version).label('max_version')
    ).group_by(Campaign.campaign_group_id).subquery('latest_version_sq')

    latest_campaigns = db.query(Campaign).join(
        latest_version_subquery,
        (Campaign.campaign_group_id == latest_version_subquery.c.campaign_group_id) &
        (Campaign.version == latest_version_subquery.c.max_version)
    ).order_by(desc(Campaign.created_at)).offset(skip).limit(limit).all()
    return latest_campaigns

def get_campaigns_by_status(db: Session, status: str, skip: int = 0, limit: int = 50):
    """Get campaigns filtered by status"""
    return db.query(Campaign).filter(
        Campaign.status == status
    ).order_by(desc(Campaign.created_at)).offset(skip).limit(limit).all()

def get_campaign_history(db: Session, campaign_group_id: uuid.UUID):
    return db.query(Campaign).filter(Campaign.campaign_group_id == campaign_group_id).order_by(desc(Campaign.version)).all()

def get_campaign_by_id(db: Session, campaign_id: uuid.UUID):
    return db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()

def update_campaign_batch_id(db: Session, campaign_id: uuid.UUID, batch_id: str):
    """
    Finds a campaign by its internal ID and updates it with the new batch_id.
    """
    db_campaign = get_campaign_by_id(db, campaign_id)
    if db_campaign:
        db_campaign.batch_id = batch_id
        # Also update the status to active when batch is created
        if db_campaign.status == "draft":
            db_campaign.status = "active"
        db.commit()
        db.refresh(db_campaign)
    return db_campaign

def create_new_campaign(db: Session, campaign: CampaignCreate):
    """Create a new campaign with proper validation"""
    new_group_id = uuid.uuid4()
    
    # Convert the Pydantic model to dict and create the Campaign
    campaign_data = campaign.model_dump()
    campaign_data.update({
        "campaign_group_id": new_group_id,
        "version": 1,
        "status": "draft"  # Ensure new campaigns start as draft
    })
    
    db_campaign = Campaign(**campaign_data)
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign

def create_new_version(db: Session, campaign_id: uuid.UUID, updates: CampaignUpdate):
    original_campaign = get_campaign_by_id(db, campaign_id)
    if not original_campaign:
        return None

    latest_version = db.query(func.max(Campaign.version)).filter(
        Campaign.campaign_group_id == original_campaign.campaign_group_id
    ).scalar() or 0

    update_data = updates.model_dump(exclude_unset=True)
    new_version_campaign = Campaign(
        campaign_group_id=original_campaign.campaign_group_id,
        version=latest_version + 1,
        campaign_name=update_data.get('campaign_name', original_campaign.campaign_name),
        agent_name=update_data.get('agent_name', original_campaign.agent_name),
        task=update_data.get('task', original_campaign.task),
        voice=update_data.get('voice', original_campaign.voice),
        pathway_id=update_data.get('pathway_id', original_campaign.pathway_id),
        start_date=update_data.get('start_date', original_campaign.start_date),
        end_date=update_data.get('end_date', original_campaign.end_date),
        contact_list=update_data.get('contact_list', original_campaign.contact_list),
        status=update_data.get('status', original_campaign.status)
    )
    db.add(new_version_campaign)
    db.commit()
    db.refresh(new_version_campaign)
    return new_version_campaign

def update_campaign_status(db: Session, campaign_id: uuid.UUID, status: str):
    """Update campaign status"""
    db_campaign = get_campaign_by_id(db, campaign_id)
    if db_campaign:
        db_campaign.status = status
        db.commit()
        db.refresh(db_campaign)
    return db_campaign

def delete_campaign(db: Session, campaign_id: uuid.UUID):
    """Soft delete a campaign by marking as inactive"""
    db_campaign = get_campaign_by_id(db, campaign_id)
    if db_campaign:
        db_campaign.status = "cancelled"  # Use cancelled instead of delete
        db.commit()
        return True
    return False

def duplicate_campaign(db: Session, campaign_id: uuid.UUID):
    """Create a duplicate of an existing campaign"""
    original = get_campaign_by_id(db, campaign_id)
    if not original:
        return None
    
    # Create a new campaign with the same data but new IDs
    duplicate_data = {
        "campaign_name": f"{original.campaign_name} (Copy)",
        "agent_name": original.agent_name,
        "task": original.task,
        "voice": original.voice,
        "pathway_id": original.pathway_id,
        "start_date": original.start_date,
        "end_date": original.end_date,
        "contact_list": original.contact_list
    }
    
    from schemas.campaign_schemas import CampaignCreate
    campaign_create = CampaignCreate(**duplicate_data)
    return create_new_campaign(db, campaign_create)

def get_campaign_analytics(db: Session, campaign_id: uuid.UUID):
    """Get analytics for a campaign"""
    # This would typically join with calls table
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        return None
    
    # Basic analytics - extend as needed
    return {
        "campaign_id": str(campaign.campaign_id),
        "campaign_name": campaign.campaign_name,
        "status": campaign.status,
        "contact_count": len(campaign.contact_list) if campaign.contact_list else 0,
        "created_at": campaign.created_at,
        "batch_id": campaign.batch_id
    }

def get_campaign_calls(db: Session, campaign_id: uuid.UUID, skip: int = 0, limit: int = 100):
    """Get calls for a specific campaign"""
    campaign = get_campaign_by_id(db, campaign_id)
    if not campaign:
        return []
    
    # This would join with the calls table
    # For now, return empty list - implement when calls table relationship is set up
    return []

def get_campaigns_summary(db: Session):
    """Get summary statistics for all campaigns"""
    total_campaigns = db.query(Campaign).count()
    active_campaigns = db.query(Campaign).filter(Campaign.status == "active").count()
    draft_campaigns = db.query(Campaign).filter(Campaign.status == "draft").count()
    completed_campaigns = db.query(Campaign).filter(Campaign.status == "completed").count()
    
    return {
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "draft_campaigns": draft_campaigns,
        "completed_campaigns": completed_campaigns
    }