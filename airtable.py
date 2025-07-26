"""
Airtable API client for fetching records with proper pagination and filtering
"""
import requests
from typing import List, Dict, Any, Optional


def fetch_all_records(
    api_key: str,
    base_id: str,
    table_name: str,
    since: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch all records from Airtable with proper pagination.
    
    Args:
        api_key: Airtable API key
        base_id: Airtable base ID
        table_name: Name of the table to fetch from
        since: ISO timestamp to fetch records modified since (for incremental updates)
    
    Returns:
        List of Airtable record dictionaries
    """
    if not api_key or not base_id:
        raise ValueError("Airtable API key and base ID are required")
    
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    all_records = []
    offset = None
    
    while True:
        params = {"pageSize": 100}
        
        # Build filter conditions
        filter_conditions = []
        
        # Always filter for 2025 records
        filter_conditions.append("YEAR({Created}) = 2025")
        
        # Add incremental filter if provided
        if since:
            filter_conditions.append(f"OR({{Created}} > '{since}', {{Last Modified Time}} > '{since}')")
        
        # Combine filters
        if len(filter_conditions) == 1:
            params["filterByFormula"] = filter_conditions[0]
        else:
            params["filterByFormula"] = f"AND({', '.join(filter_conditions)})"
        
        # Add pagination offset
        if offset:
            params["offset"] = offset
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Airtable API error {response.status_code}: {response.text}")
        
        data = response.json()
        records = data.get("records", [])
        
        if not records:
            break
        
        all_records.extend(records)
        offset = data.get("offset")
        
        if not offset:
            break
    
    return all_records