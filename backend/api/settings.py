"""
Settings API Endpoints
System configuration and user preferences management
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
import logging
import json
from datetime import datetime

from backend.core.database import db_manager, create_tables

router = APIRouter(prefix="/settings", tags=["Settings"])
logger = logging.getLogger(__name__)


class Setting:
    """Setting data model"""
    def __init__(self, key: str, value: Any, **kwargs):
        self.key = key
        self.value = value
        self.category = kwargs.get('category', 'general')
        self.description = kwargs.get('description', '')
        self.data_type = kwargs.get('data_type', 'string')
        self.is_public = kwargs.get('is_public', True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "description": self.description,
            "data_type": self.data_type,
            "is_public": self.is_public
        }


@router.get("/", response_model=List[Dict[str, Any]])
async def get_settings(
    category: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(None)
):
    """Get system settings with optional filtering"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Build query
        query = "SELECT * FROM settings"
        params = []
        conditions = []

        if category:
            conditions.append("category = ?")
            params.append(category)

        if is_public is not None:
            conditions.append("is_public = ?")
            params.append(is_public)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY category, key"

        # Execute query
        results = db_manager.execute_query(query, tuple(params))

        # Parse JSON values where needed
        for result in results:
            if result.get('data_type') in ['json', 'object', 'array']:
                try:
                    result['value'] = json.loads(result['value'])
                except:
                    pass

        logger.info(f"Retrieved {len(results)} settings")
        return results

    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/categories", response_model=List[str])
async def get_setting_categories():
    """Get all available setting categories"""

    try:
        await create_tables()

        query = "SELECT DISTINCT category FROM settings ORDER BY category"
        results = db_manager.execute_query(query)

        categories = [row["category"] for row in results]
        logger.info(f"Retrieved {len(categories)} setting categories")
        return categories

    except Exception as e:
        logger.error(f"Error getting setting categories: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/key/{setting_key}", response_model=Dict[str, Any])
async def get_setting(setting_key: str):
    """Get a specific setting by key"""

    try:
        query = "SELECT * FROM settings WHERE key = ?"
        results = db_manager.execute_query(query, (setting_key,))

        if not results:
            raise HTTPException(status_code=404, detail="Setting not found")

        result = results[0]

        # Parse JSON values where needed
        if result.get('data_type') in ['json', 'object', 'array']:
            try:
                result['value'] = json.loads(result['value'])
            except:
                pass

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting setting {setting_key}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_setting(setting_data: Dict[str, Any]):
    """Create a new setting"""

    try:
        # Validate required fields
        if not setting_data.get("key"):
            raise HTTPException(status_code=400, detail="Key is required")

        if "value" not in setting_data:
            raise HTTPException(status_code=400, detail="Value is required")

        # Check if setting already exists
        existing = db_manager.execute_query(
            "SELECT id FROM settings WHERE key = ?",
            (setting_data["key"],)
        )
        if existing:
            raise HTTPException(status_code=400, detail="Setting already exists")

        # Ensure database tables exist
        await create_tables()

        # Create setting object
        setting = Setting(
            key=setting_data["key"],
            value=setting_data["value"],
            **setting_data
        )

        # Serialize value if it's complex
        value = setting.value
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
            setting.data_type = 'json'

        # Insert into database
        query = """
        INSERT INTO settings (key, value, category, description, data_type, is_public)
        VALUES (?, ?, ?, ?, ?, ?)
        """

        setting_id = db_manager.execute_insert(
            query,
            (setting.key, str(value), setting.category, setting.description,
             setting.data_type, setting.is_public)
        )

        result = setting.to_dict()
        result["id"] = setting_id

        logger.info(f"Created setting: {setting.key}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating setting: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/", response_model=Dict[str, Any])
async def bulk_update_settings(settings_data: Dict[str, Any]):
    """Bulk update settings (frontend contract: PUT /api/settings)"""
    try:
        await create_tables()
        updated = []
        for key, value in settings_data.items():
            serialized = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            existing = db_manager.execute_query(
                "SELECT id FROM settings WHERE key = ?", (key,)
            )
            if existing:
                db_manager.execute_write(
                    "UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
                    (serialized, key),
                )
            else:
                db_manager.execute_insert(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    (key, serialized),
                )
            updated.append(key)
        return {"message": f"Updated {len(updated)} settings", "updated_keys": updated}
    except Exception as e:
        logger.error(f"Error bulk updating settings: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/key/{setting_key}", response_model=Dict[str, Any])
async def update_setting(setting_key: str, setting_data: Dict[str, Any]):
    """Update an existing setting"""

    try:
        # Check if setting exists
        existing = db_manager.execute_query(
            "SELECT * FROM settings WHERE key = ?",
            (setting_key,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Setting not found")

        # Prepare update data
        value = setting_data.get("value", existing[0]["value"])
        category = setting_data.get("category", existing[0]["category"])
        description = setting_data.get("description", existing[0]["description"])
        data_type = setting_data.get("data_type", existing[0]["data_type"])
        is_public = setting_data.get("is_public", existing[0]["is_public"])

        # Serialize value if it's complex
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
            data_type = 'json'

        # Update setting
        query = """
        UPDATE settings
        SET value = ?, category = ?, description = ?, data_type = ?,
            is_public = ?, updated_at = CURRENT_TIMESTAMP
        WHERE key = ?
        """

        db_manager.execute_insert(
            query,
            (str(value), category, description, data_type, is_public, setting_key)
        )

        # Get updated setting
        updated = db_manager.execute_query(
            "SELECT * FROM settings WHERE key = ?",
            (setting_key,)
        )

        result = updated[0]

        # Parse JSON values where needed
        if result.get('data_type') in ['json', 'object', 'array']:
            try:
                result['value'] = json.loads(result['value'])
            except:
                pass

        logger.info(f"Updated setting: {setting_key}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating setting {setting_key}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/key/{setting_key}")
async def delete_setting(setting_key: str):
    """Delete a specific setting"""

    try:
        # Check if setting exists
        existing = db_manager.execute_query(
            "SELECT id FROM settings WHERE key = ?",
            (setting_key,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Setting not found")

        # Delete setting
        query = "DELETE FROM settings WHERE key = ?"
        db_manager.execute_insert(query, (setting_key,))

        logger.info(f"Deleted setting: {setting_key}")
        return {"message": "Setting deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting setting {setting_key}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/bulk", response_model=Dict[str, Any])
async def update_settings_bulk(settings_data: Dict[str, Any]):
    """Update multiple settings at once"""

    try:
        if not settings_data or not isinstance(settings_data, dict):
            raise HTTPException(status_code=400, detail="Invalid settings data")

        # Ensure database tables exist
        await create_tables()

        updated_count = 0
        created_count = 0
        errors = []

        for key, value in settings_data.items():
            try:
                # Check if setting exists
                existing = db_manager.execute_query(
                    "SELECT id FROM settings WHERE key = ?",
                    (key,)
                )

                # Serialize value if complex
                serialized_value = value
                data_type = 'string'
                if isinstance(value, (dict, list)):
                    serialized_value = json.dumps(value)
                    data_type = 'json'
                elif isinstance(value, bool):
                    data_type = 'boolean'
                elif isinstance(value, (int, float)):
                    data_type = 'number'

                if existing:
                    # Update existing setting
                    update_query = """
                    UPDATE settings
                    SET value = ?, data_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE key = ?
                    """
                    db_manager.execute_insert(
                        update_query,
                        (str(serialized_value), data_type, key)
                    )
                    updated_count += 1
                else:
                    # Create new setting
                    create_query = """
                    INSERT INTO settings (key, value, data_type, category, is_public)
                    VALUES (?, ?, ?, 'general', 1)
                    """
                    db_manager.execute_insert(
                        create_query,
                        (key, str(serialized_value), data_type)
                    )
                    created_count += 1

            except Exception as e:
                errors.append(f"Error with setting '{key}': {str(e)}")

        result = {
            "message": "Bulk settings update completed",
            "updated_count": updated_count,
            "created_count": created_count,
            "total_processed": updated_count + created_count,
            "errors": errors
        }

        if errors:
            result["status"] = "partial_success"
        else:
            result["status"] = "success"

        logger.info(f"Bulk updated {updated_count} and created {created_count} settings")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk settings update: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/defaults/reset", response_model=Dict[str, Any])
async def reset_to_defaults():
    """Reset all settings to default values"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Default settings
        default_settings = {
            "system.app_name": "OSINT E-post Etterforsker",
            "system.version": "1.0.0",
            "system.timezone": "Europe/Oslo",
            "system.language": "en",
            "system.theme": "light",

            "crawler.max_threads": 5,
            "crawler.delay_seconds": 2,
            "crawler.timeout_seconds": 30,
            "crawler.max_pages_per_source": 100,
            "crawler.user_agent": "OSINT-Crawler/1.0",

            "email.verification_enabled": True,
            "email.verification_timeout": 10,
            "email.max_retries": 3,
            "email.bounce_handling": True,

            "scoring.min_confidence": 60.0,
            "scoring.auto_verify_threshold": 85.0,
            "scoring.manual_review_threshold": 70.0,

            "export.max_file_size_mb": 50,
            "export.retention_days": 30,
            "export.allowed_formats": ["csv", "json", "xlsx"],

            "security.session_timeout_minutes": 480,
            "security.max_login_attempts": 5,
            "security.password_min_length": 8,

            "notification.email_enabled": True,
            "notification.webhook_enabled": False,
            "notification.slack_enabled": False
        }

        # Clear existing settings
        db_manager.execute_insert("DELETE FROM settings", ())

        # Insert default settings
        created_count = 0
        for key, value in default_settings.items():
            try:
                # Determine category from key prefix
                category = key.split('.')[0] if '.' in key else 'general'

                # Determine data type
                data_type = 'string'
                if isinstance(value, bool):
                    data_type = 'boolean'
                elif isinstance(value, (int, float)):
                    data_type = 'number'
                elif isinstance(value, list):
                    value = json.dumps(value)
                    data_type = 'json'

                query = """
                INSERT INTO settings (key, value, category, data_type, is_public)
                VALUES (?, ?, ?, ?, 1)
                """

                db_manager.execute_insert(
                    query,
                    (key, str(value), category, data_type)
                )
                created_count += 1

            except Exception as e:
                logger.error(f"Error creating default setting {key}: {e}")

        logger.info(f"Reset to defaults: created {created_count} settings")
        return {
            "message": "Settings reset to defaults successfully",
            "created_count": created_count,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error resetting to defaults: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/export/all", response_model=Dict[str, Any])
async def export_all_settings():
    """Export all settings as JSON"""

    try:
        await create_tables()

        query = "SELECT * FROM settings ORDER BY category, key"
        results = db_manager.execute_query(query)

        # Group by category
        export_data = {}
        for result in results:
            category = result["category"]
            if category not in export_data:
                export_data[category] = {}

            value = result["value"]
            if result.get('data_type') in ['json', 'object', 'array']:
                try:
                    value = json.loads(value)
                except:
                    pass
            elif result.get('data_type') == 'boolean':
                value = value.lower() in ('true', '1', 'yes')
            elif result.get('data_type') == 'number':
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except:
                    pass

            export_data[category][result["key"]] = {
                "value": value,
                "description": result.get("description", ""),
                "data_type": result.get("data_type", "string"),
                "is_public": result.get("is_public", True)
            }

        logger.info(f"Exported {len(results)} settings")
        return {
            "message": "Settings exported successfully",
            "export_date": datetime.now().isoformat(),
            "total_settings": len(results),
            "settings": export_data
        }

    except Exception as e:
        logger.error(f"Error exporting settings: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")