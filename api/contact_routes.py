import io
import csv
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from schemas.contact_schemas import ContactCreate, ContactUpdate, ContactRead, ContactBatchCreate
from crud import db_contact
from core.database import get_db
from utils.validators import validate_phone_number
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contacts", tags=["Contacts"])

@router.post("/", response_model=ContactRead)
def create_contact_api(contact: ContactCreate, db: Session = Depends(get_db)):
    """Create a single contact with validation"""
    try:
        new_contact = db_contact.create_contact(db=db, contact=contact)
        return new_contact
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating contact: {e}")
        raise HTTPException(status_code=500, detail="Failed to create contact")

@router.get("/", response_model=List[ContactRead])
def get_contacts_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all contacts with pagination"""
    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")
    return db_contact.get_contacts(db=db, skip=skip, limit=limit)

@router.get("/{contact_id}", response_model=ContactRead)
def get_contact_api(contact_id: int, db: Session = Depends(get_db)):
    """Get a specific contact by ID"""
    contact = db_contact.get_contact(db=db, contact_id=contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.put("/{contact_id}", response_model=ContactRead)
def update_contact_api(contact_id: int, contact_update: ContactUpdate, db: Session = Depends(get_db)):
    """Update a contact"""
    try:
        updated_contact = db_contact.update_contact(db=db, contact_id=contact_id, contact_update=contact_update)
        if not updated_contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return updated_contact
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update contact")

@router.delete("/{contact_id}")
def delete_contact_api(contact_id: int, db: Session = Depends(get_db)):
    """Delete a contact"""
    try:
        deleted = db_contact.delete_contact(db=db, contact_id=contact_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Contact not found")
        return {"success": True, "message": "Contact deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete contact")

@router.post("/batch", response_model=dict)
def create_contacts_batch(contacts: List[ContactCreate], db: Session = Depends(get_db)):
    """Create multiple contacts at once"""
    if len(contacts) > 1000:
        raise HTTPException(status_code=400, detail="Cannot create more than 1000 contacts at once")
    
    created_contacts = []
    errors = []
    
    for i, contact in enumerate(contacts):
        try:
            created = db_contact.validate_and_create_contact(db, contact)
            created_contacts.append(created)
        except ValueError as e:
            errors.append(f"Row {i+1}: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating contact {i+1}: {e}")
            errors.append(f"Row {i+1}: Database error")
    
    return {
        "success": True,
        "created": len(created_contacts),
        "errors": len(errors),
        "error_details": errors,
        "contacts": created_contacts
    }

@router.post("/import", response_model=dict)
async def import_contacts_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import contacts from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))
        
        contacts_to_create = []
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=1):
            try:
                # Map CSV columns to contact fields
                contact_data = {
                    'name': row.get('name', '').strip(),
                    'phone_number': row.get('phone_number', '').strip(),
                    'company_name': row.get('company_name', '').strip() or None,
                    'email': row.get('email', '').strip() or None,
                    'tags': row.get('tags', '').strip() or None
                }
                
                if not contact_data['name']:
                    errors.append(f"Row {row_num}: Name is required")
                    continue
                    
                if not contact_data['phone_number']:
                    errors.append(f"Row {row_num}: Phone number is required")
                    continue
                
                contact = ContactCreate(**contact_data)
                contacts_to_create.append(contact)
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        # Create contacts in batch
        created_contacts = []
        for i, contact in enumerate(contacts_to_create):
            try:
                created = db_contact.validate_and_create_contact(db, contact)
                created_contacts.append(created)
            except ValueError as e:
                errors.append(f"Contact '{contact.name}': {str(e)}")
            except Exception as e:
                logger.error(f"Error creating contact '{contact.name}': {e}")
                errors.append(f"Contact '{contact.name}': Database error")
        
        return {
            "success": True,
            "message": f"Import completed. Created {len(created_contacts)} contacts.",
            "created": len(created_contacts),
            "errors": len(errors),
            "error_details": errors[:10],  # Limit error details to first 10
            "total_errors": len(errors)
        }
        
    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        raise HTTPException(status_code=500, detail="Failed to process CSV file")

@router.get("/search/{query}")
def search_contacts(query: str, db: Session = Depends(get_db)):
    """Search contacts by name, phone, or company"""
    try:
        contacts = db_contact.search_contacts(db=db, query=query)
        return {"success": True, "contacts": contacts}
    except Exception as e:
        logger.error(f"Error searching contacts: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/stats/summary")
def get_contact_stats(db: Session = Depends(get_db)):
    """Get contact statistics"""
    try:
        stats = db_contact.get_contact_statistics(db=db)
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting contact stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")