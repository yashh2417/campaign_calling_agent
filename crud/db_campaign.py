import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.campaign import Campaign
from schemas.campaign_schemas import CampaignCreate, CampaignUpdate

def get_latest_campaigns_grouped(db: Session):
    latest_version_subquery = db.query(
        Campaign.campaign_group_id,
        func.max(Campaign.version).label('max_version')
    ).group_by(Campaign.campaign_group_id).subquery('latest_version_sq')

    latest_campaigns = db.query(Campaign).join(
        latest_version_subquery,
        (Campaign.campaign_group_id == latest_version_subquery.c.campaign_group_id) &
        (Campaign.version == latest_version_subquery.c.max_version)
    ).order_by(desc(Campaign.created_at)).all()
    return latest_campaigns

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
        db.commit()
        db.refresh(db_campaign)
    return db_campaign

def create_new_campaign(db: Session, campaign: CampaignCreate):
    new_group_id = uuid.uuid4()
    db_campaign = Campaign(**campaign.model_dump(), campaign_group_id=new_group_id, version=1)
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