#!/usr/bin/env python3
"""
Test cache locally to debug issues
"""
from cache_manager import airtable_cache

def test_cache():
    print("Testing cache functionality...")
    
    # Force fresh data
    data = airtable_cache.get_data(force_refresh=True)
    
    print(f"Retrieved {len(data)} records")
    
    if data:
        # Check first few records for field mappings
        for i, record in enumerate(data[:3], 1):
            print(f"\nRecord {i}:")
            print(f"  ID: {record.get('id', 'N/A')}")
            print(f"  Environment: {record.get('environment', 'N/A')}")
            print(f"  Area Impacted: {record.get('area_impacted', 'N/A')}")
            print(f"  Team: {record.get('team_routed', 'N/A')}")
            print(f"  Description: {record.get('initial_description', 'N/A')[:100]}...")
        
        # Show environment distribution
        env_counts = {}
        team_counts = {}
        area_counts = {}
        
        for record in data:
            env = record.get('environment', 'Unknown')
            team = record.get('team_routed', 'Unknown')
            area = record.get('area_impacted', 'Unknown')
            
            env_counts[env] = env_counts.get(env, 0) + 1
            team_counts[team] = team_counts.get(team, 0) + 1
            area_counts[area] = area_counts.get(area, 0) + 1
        
        print(f"\nEnvironment distribution:")
        for env, count in sorted(env_counts.items()):
            print(f"  {env}: {count}")
        
        print(f"\nTeam distribution:")
        for team, count in sorted(team_counts.items()):
            print(f"  {team}: {count}")
        
        print(f"\nArea Impacted distribution (top 10):")
        for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {area}: {count}")
    
    else:
        print("No data retrieved!")

if __name__ == "__main__":
    test_cache()