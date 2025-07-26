"""
Airtable API client for fetching records with proper pagination and filtering
"""
import requests
import time
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
        
        # Retry logic with exponential backoff
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    break
                elif response.status_code == 429:  # Rate limit
                    if attempt < 2:
                        wait_time = 2 ** attempt
                        print(f"⚠️ Rate limited, waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Airtable rate limit exceeded after 3 attempts")
                else:
                    if attempt < 2:
                        wait_time = 2 ** attempt
                        print(f"⚠️ Airtable API error {response.status_code}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Airtable API error {response.status_code}: {response.text}")
                        
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    wait_time = 2 ** attempt
                    print(f"⚠️ Request failed: {e}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Airtable request failed after 3 attempts: {e}")
        
        data = response.json()
        records = data.get("records", [])
        
        if not records:
            break
        
        all_records.extend(records)
        offset = data.get("offset")
        
        if not offset:
            break
    
    return all_records