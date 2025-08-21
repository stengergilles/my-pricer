"""
Request validation utilities.
"""

from typing import Dict, Any

# Validation schemas
analysis_schema = {
    'crypto_id': {'type': str, 'required': True},
    'strategy_name': {'type': str, 'required': False},
    'timeframe': {'type': int, 'required': False, 'min': 1, 'max': 365},
    'parameters': {'type': dict, 'required': False}
}

backtest_schema = {
    'crypto_id': {'type': str, 'required': True},
    'strategy_name': {'type': str, 'required': True},
    'parameters': {'type': dict, 'required': True},
    'timeframe': {'type': int, 'required': False, 'min': 1, 'max': 365}
}

def validate_request_data(data: Dict[str, Any], schema: Dict[str, Dict]) -> Dict[str, Any]:
    """Validate request data against schema."""
    if not data:
        raise ValueError("Request data is required")
    
    validated = {}
    errors = []
    
    for field, rules in schema.items():
        value = data.get(field)
        
        # Check required fields
        if rules.get('required', False) and value is None:
            errors.append(f"Field '{field}' is required")
            continue
        
        # Skip validation for optional fields that are None
        if value is None:
            continue
        
        # Type validation
        expected_type = rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"Field '{field}' must be of type {expected_type.__name__}")
            continue
        
        # Range validation for integers
        if isinstance(value, int):
            if 'min' in rules and value < rules['min']:
                errors.append(f"Field '{field}' must be >= {rules['min']}")
                continue
            if 'max' in rules and value > rules['max']:
                errors.append(f"Field '{field}' must be <= {rules['max']}")
                continue
        
        validated[field] = value
    
    if errors:
        raise ValueError(f"Validation errors: {', '.join(errors)}")
    
    return validated
