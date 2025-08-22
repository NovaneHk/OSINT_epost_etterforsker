"""
Input Validation Utilities
Comprehensive validation functions for OSINT application data
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from email_validator import validate_email, EmailNotValidError

from .exceptions import ValidationError, InvalidEmailError, InvalidSearchCriteriaError


def validate_email_address(email: str) -> str:
    """Validate email address format and return normalized version"""
    if not email or not isinstance(email, str):
        raise InvalidEmailError(email or "")

    try:
        # Use email-validator library for comprehensive validation
        valid = validate_email(email.strip())
        return valid.email
    except EmailNotValidError as e:
        raise InvalidEmailError(email) from e


def validate_phone_number(phone: str) -> str:
    """Validate and normalize phone number"""
    if not phone:
        return phone

    # Remove common separators and spaces
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)

    # Basic phone number pattern (supports international format)
    phone_pattern = r'^\+?[1-9]\d{7,14}$'

    if not re.match(phone_pattern, cleaned):
        raise ValidationError(f"Invalid phone number format: {phone}", "phone")

    return cleaned


def validate_url(url: str) -> str:
    """Validate URL format"""
    if not url:
        return url

    # Basic URL pattern
    url_pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'

    if not re.match(url_pattern, url, re.IGNORECASE):
        raise ValidationError(f"Invalid URL format: {url}", "url")

    return url.lower()


def validate_json_string(json_str: str, field_name: str = "json_field") -> Dict[str, Any]:
    """Validate and parse JSON string"""
    if not json_str:
        return {}

    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        if not isinstance(data, dict):
            raise ValidationError(f"JSON must be an object, got {type(data).__name__}", field_name)
        return data
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON format: {str(e)}", field_name)
    except TypeError as e:
        raise ValidationError(f"JSON parsing error: {str(e)}", field_name)


def validate_search_criteria(criteria: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Validate search criteria structure"""
    if isinstance(criteria, str):
        criteria = validate_json_string(criteria, "search_criteria")

    if not isinstance(criteria, dict):
        raise InvalidSearchCriteriaError("Search criteria must be a JSON object")

    # Define allowed search fields
    allowed_fields = {
        'keywords', 'companies', 'job_titles', 'locations', 'industries',
        'email_domains', 'exclude_keywords', 'confidence_min', 'confidence_max',
        'date_from', 'date_to', 'limit', 'sources'
    }

    # Check for invalid fields
    invalid_fields = set(criteria.keys()) - allowed_fields
    if invalid_fields:
        raise InvalidSearchCriteriaError(f"Invalid search fields: {', '.join(invalid_fields)}")

    # Validate specific field types
    if 'confidence_min' in criteria:
        if not isinstance(criteria['confidence_min'], (int, float)) or not 0 <= criteria['confidence_min'] <= 100:
            raise InvalidSearchCriteriaError("confidence_min must be a number between 0 and 100")

    if 'confidence_max' in criteria:
        if not isinstance(criteria['confidence_max'], (int, float)) or not 0 <= criteria['confidence_max'] <= 100:
            raise InvalidSearchCriteriaError("confidence_max must be a number between 0 and 100")

    if 'limit' in criteria:
        if not isinstance(criteria['limit'], int) or criteria['limit'] <= 0:
            raise InvalidSearchCriteriaError("limit must be a positive integer")

    return criteria


def validate_campaign_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate campaign creation/update data"""
    required_fields = ['name']

    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(f"Field '{field}' is required", field)

    # Validate name
    if not isinstance(data['name'], str) or len(data['name'].strip()) < 2:
        raise ValidationError("Campaign name must be at least 2 characters long", "name")

    # Validate type if provided
    if 'type' in data:
        valid_types = ['manual', 'automated', 'scheduled']
        if data['type'] not in valid_types:
            raise ValidationError(f"Invalid campaign type. Must be one of: {', '.join(valid_types)}", "type")

    # Validate leads_target if provided
    if 'leads_target' in data:
        if not isinstance(data['leads_target'], int) or data['leads_target'] <= 0:
            raise ValidationError("leads_target must be a positive integer", "leads_target")

    # Validate sources if provided
    if 'sources' in data:
        if isinstance(data['sources'], str):
            try:
                sources = json.loads(data['sources'])
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON format for sources", "sources")
        else:
            sources = data['sources']

        if not isinstance(sources, list):
            raise ValidationError("Sources must be a list", "sources")

        if not sources:
            raise ValidationError("At least one source must be specified", "sources")

    # Validate filter criteria if provided
    if 'filter_criteria' in data:
        data['filter_criteria'] = validate_search_criteria(data['filter_criteria'])

    return data


def validate_source_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate source creation/update data"""
    required_fields = ['name', 'type']

    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(f"Field '{field}' is required", field)

    # Validate name
    if not isinstance(data['name'], str) or len(data['name'].strip()) < 2:
        raise ValidationError("Source name must be at least 2 characters long", "name")

    # Validate type
    valid_types = ['website', 'api', 'database', 'social_media', 'directory', 'other']
    if data['type'] not in valid_types:
        raise ValidationError(f"Invalid source type. Must be one of: {', '.join(valid_types)}", "type")

    # Validate URL if provided
    if 'url' in data and data['url']:
        data['url'] = validate_url(data['url'])

    # Validate configuration if provided
    if 'configuration' in data:
        data['configuration'] = validate_json_string(data['configuration'], "configuration")

    return data


def validate_export_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate export creation data"""
    required_fields = ['name']

    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(f"Field '{field}' is required", field)

    # Validate name
    if not isinstance(data['name'], str) or len(data['name'].strip()) < 2:
        raise ValidationError("Export name must be at least 2 characters long", "name")

    # Validate type if provided
    if 'type' in data:
        valid_types = ['csv', 'json', 'xlsx']
        if data['type'] not in valid_types:
            raise ValidationError(f"Invalid export type. Must be one of: {', '.join(valid_types)}", "type")

    # Validate filters if provided
    if 'filters' in data:
        data['filters'] = validate_json_string(data['filters'], "filters")

    return data


def validate_run_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate run creation data"""
    required_fields = ['name']

    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(f"Field '{field}' is required", field)

    # Validate name
    if not isinstance(data['name'], str) or len(data['name'].strip()) < 2:
        raise ValidationError("Run name must be at least 2 characters long", "name")

    # Validate type if provided
    if 'type' in data:
        valid_types = ['manual', 'automated', 'scheduled']
        if data['type'] not in valid_types:
            raise ValidationError(f"Invalid run type. Must be one of: {', '.join(valid_types)}", "type")

    # Validate search terms if provided
    if 'search_terms' in data:
        data['search_terms'] = validate_json_string(data['search_terms'], "search_terms")

    # Validate filters if provided
    if 'filters' in data:
        data['filters'] = validate_search_criteria(data['filters'])

    return data


def validate_setting_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate setting creation/update data"""
    required_fields = ['key', 'value']

    # Check required fields
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Field '{field}' is required", field)

    # Validate key format
    if not isinstance(data['key'], str) or not re.match(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$', data['key']):
        raise ValidationError("Setting key must be in format: category.setting_name", "key")

    # Validate data_type if provided
    if 'data_type' in data:
        valid_types = ['string', 'number', 'boolean', 'json']
        if data['data_type'] not in valid_types:
            raise ValidationError(f"Invalid data type. Must be one of: {', '.join(valid_types)}", "data_type")

    return data


def validate_pagination_params(skip: int = 0, limit: int = 50) -> tuple[int, int]:
    """Validate pagination parameters"""
    if skip < 0:
        raise ValidationError("Skip parameter must be non-negative", "skip")

    if limit <= 0 or limit > 1000:
        raise ValidationError("Limit parameter must be between 1 and 1000", "limit")

    return skip, limit


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input"""
    if not isinstance(value, str):
        return str(value)

    # Remove null bytes and control characters
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

    # Trim whitespace
    sanitized = sanitized.strip()

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def validate_confidence_score(score: Union[int, float]) -> float:
    """Validate confidence score value"""
    if not isinstance(score, (int, float)):
        raise ValidationError("Confidence score must be a number", "confidence_score")

    if not 0 <= score <= 100:
        raise ValidationError("Confidence score must be between 0 and 100", "confidence_score")

    return float(score)