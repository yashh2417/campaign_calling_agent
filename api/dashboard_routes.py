# api/dashboard_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from core.database import get_db
from models.campaign import Campaign
from models.contact import Contact
from models.call_table import Call
from schemas.user_schemas import UserRead
from api.auth_routes import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for the current user"""
    try:
        # In a production app, you would filter by user_id
        # For now, we'll return all data but you can modify these queries
        # to include WHERE clauses like: WHERE user_id = current_user.id
        
        # Get campaigns count
        total_campaigns = db.query(Campaign).count()
        active_campaigns = db.query(Campaign).filter(Campaign.status == "active").count()
        draft_campaigns = db.query(Campaign).filter(Campaign.status == "draft").count()
        
        # Get contacts count
        total_contacts = db.query(Contact).count()
        
        # Get recent calls count (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_calls = db.query(Call).filter(
            Call.created_at >= seven_days_ago
        ).count()
        
        # Get call success rate
        completed_calls = db.query(Call).filter(Call.completed == True).count()
        total_calls = db.query(Call).count()
        success_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Calculate growth metrics (compared to previous period)
        fourteen_days_ago = datetime.now() - timedelta(days=14)
        previous_period_calls = db.query(Call).filter(
            Call.created_at >= fourteen_days_ago,
            Call.created_at < seven_days_ago
        ).count()
        
        call_growth = ((recent_calls - previous_period_calls) / previous_period_calls * 100) if previous_period_calls > 0 else 0
        
        logger.info(f"Dashboard stats requested by user: {current_user.email}")
        
        return {
            "success": True,
            "stats": {
                "total_campaigns": total_campaigns,
                "active_campaigns": active_campaigns,
                "draft_campaigns": draft_campaigns,
                "total_contacts": total_contacts,
                "recent_calls": recent_calls,
                "total_calls": total_calls,
                "success_rate": round(success_rate, 1),
                "call_growth": round(call_growth, 1)
            }
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard statistics")

@router.get("/recent-activity")
def get_recent_activity(
    limit: int = 10,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent activity for the dashboard"""
    try:
        # Get recent calls
        recent_calls = db.query(Call).order_by(desc(Call.created_at)).limit(limit).all()
        
        # Get recent campaigns
        recent_campaigns = db.query(Campaign).order_by(desc(Campaign.created_at)).limit(limit).all()
        
        activity = []
        
        # Add calls to activity
        for call in recent_calls:
            activity.append({
                "type": "call",
                "id": call.call_id,
                "description": f"Call to {call.to_phone or 'Unknown'}",
                "status": "completed" if call.completed else "in_progress",
                "timestamp": call.created_at,
                "details": {
                    "phone": call.to_phone,
                    "duration": call.call_duration,
                    "emotion": call.emotion
                }
            })
        
        # Add campaigns to activity
        for campaign in recent_campaigns:
            activity.append({
                "type": "campaign",
                "id": str(campaign.campaign_id),
                "description": f"Campaign '{campaign.campaign_name}' {campaign.status}",
                "status": campaign.status,
                "timestamp": campaign.created_at,
                "details": {
                    "agent_name": campaign.agent_name,
                    "voice": campaign.voice,
                    "contact_count": len(campaign.contact_list) if campaign.contact_list else 0
                }
            })
        
        # Sort by timestamp (most recent first)
        activity.sort(key=lambda x: x["timestamp"], reverse=True)
        
        logger.info(f"Recent activity requested by user: {current_user.email}")
        
        return {
            "success": True,
            "activity": activity[:limit]
        }
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent activity")

@router.get("/analytics")
def get_dashboard_analytics(
    days: int = 30,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics data for charts and graphs"""
    try:
        # Get date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get daily call counts
        daily_calls = db.query(
            func.date(Call.created_at).label('date'),
            func.count(Call.call_id).label('count')
        ).filter(
            Call.created_at >= start_date
        ).group_by(
            func.date(Call.created_at)
        ).order_by('date').all()
        
        # Get call status distribution
        call_status_dist = db.query(
            Call.completed.label('status'),
            func.count(Call.call_id).label('count')
        ).filter(
            Call.created_at >= start_date
        ).group_by(Call.completed).all()
        
        # Get campaign status distribution
        campaign_status_dist = db.query(
            Campaign.status.label('status'),
            func.count(Campaign.campaign_id).label('count')
        ).group_by(Campaign.status).all()
        
        # Get emotion distribution from calls
        emotion_dist = db.query(
            Call.emotion.label('emotion'),
            func.count(Call.call_id).label('count')
        ).filter(
            Call.created_at >= start_date,
            Call.emotion.isnot(None)
        ).group_by(Call.emotion).all()
        
        # Format data for frontend
        daily_calls_data = [
            {"date": str(item.date), "calls": item.count}
            for item in daily_calls
        ]
        
        call_status_data = [
            {"status": "Completed" if item.status else "In Progress", "count": item.count}
            for item in call_status_dist
        ]
        
        campaign_status_data = [
            {"status": item.status.title(), "count": item.count}
            for item in campaign_status_dist
        ]
        
        emotion_data = [
            {"emotion": item.emotion.title() if item.emotion else "Unknown", "count": item.count}
            for item in emotion_dist
        ]
        
        return {
            "success": True,
            "analytics": {
                "daily_calls": daily_calls_data,
                "call_status_distribution": call_status_data,
                "campaign_status_distribution": campaign_status_data,
                "emotion_distribution": emotion_data,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting dashboard analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics data")

@router.get("/performance")
def get_performance_metrics(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance metrics for the dashboard"""
    try:
        # Get average call duration
        avg_duration = db.query(func.avg(Call.call_duration)).filter(
            Call.call_duration.isnot(None)
        ).scalar() or 0
        
        # Get completion rate
        total_calls = db.query(Call).count()
        completed_calls = db.query(Call).filter(Call.completed == True).count()
        completion_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Get most successful campaign
        most_successful_campaign = db.query(
            Campaign.campaign_name,
            func.count(Call.call_id).label('call_count')
        ).join(
            Call, Campaign.campaign_id == Call.campaign_id
        ).filter(
            Call.completed == True
        ).group_by(
            Campaign.campaign_id, Campaign.campaign_name
        ).order_by(
            desc('call_count')
        ).first()
        
        # Get busiest time of day
        busiest_hour = db.query(
            func.extract('hour', Call.created_at).label('hour'),
            func.count(Call.call_id).label('count')
        ).group_by(
            func.extract('hour', Call.created_at)
        ).order_by(
            desc('count')
        ).first()
        
        return {
            "success": True,
            "performance": {
                "average_call_duration": round(avg_duration, 2) if avg_duration else 0,
                "completion_rate": round(completion_rate, 1),
                "total_calls": total_calls,
                "completed_calls": completed_calls,
                "most_successful_campaign": {
                    "name": most_successful_campaign.campaign_name if most_successful_campaign else "N/A",
                    "call_count": most_successful_campaign.call_count if most_successful_campaign else 0
                },
                "busiest_hour": {
                    "hour": int(busiest_hour.hour) if busiest_hour else 0,
                    "call_count": busiest_hour.count if busiest_hour else 0
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")
