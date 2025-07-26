"""
Jira-based team assignment using semantic similarity
"""
import os
import sys
from typing import Dict, Any, List
import sqlite3

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from semantic_router import find_related_tickets
except ImportError:
    print("Warning: Could not import semantic_router, team assignment will fallback to 'Triage'")
    find_related_tickets = None

from config import DB_PATH

def analyze_team_assignment(issue_description: str, issue_type: str = "", status: str = "", area_impacted: str = "") -> str:
    """
    Use Jira ticket matching to determine team assignment based on semantic similarity.
    
    Args:
        issue_description: The main description/notes of the issue
        issue_type: Type of issue (if available)
        status: Current status (if available) 
        area_impacted: Area/system impacted (if available)
    
    Returns:
        Team name as string
    """
    if not find_related_tickets or not issue_description:
        return "Triage"  # Fallback if no semantic router or description
    
    try:
        # Find the most similar Jira tickets
        jira_matches = find_related_tickets(issue_description, top_n=3)
        
        if not jira_matches:
            return "Triage"
        
        # Get the team from the best match (highest similarity)
        best_match = jira_matches[0]
        similarity, jira_id, jira_summary, assignee, team_name = best_match
        
        # Only use the match if similarity is reasonable (>0.7)
        if similarity > 0.7 and team_name:
            print(f"Matched to Jira {jira_id} (similarity: {similarity:.3f}) -> Team: {team_name}")
            return team_name
        
        # If similarity is moderate (0.5-0.7), consider multiple matches
        elif similarity > 0.5:
            # Count team votes from top 3 matches
            team_votes = {}
            for sim, j_id, j_sum, j_assignee, j_team in jira_matches:
                if sim > 0.5 and j_team:
                    team_votes[j_team] = team_votes.get(j_team, 0) + sim
            
            if team_votes:
                # Return team with highest weighted vote
                best_team = max(team_votes.items(), key=lambda x: x[1])
                print(f"Team consensus from Jira matches: {best_team[0]} (score: {best_team[1]:.3f})")
                return best_team[0]
        
        print(f"Low similarity ({similarity:.3f}) to Jira tickets, defaulting to Triage")
        return "Triage"
        
    except Exception as e:
        print(f"Error in Jira team analysis: {e}")
        return "Triage"

def analyze_team_batch(issues: list) -> Dict[str, str]:
    """
    Analyze multiple issues for team assignment using Jira ticket matching.
    
    Args:
        issues: List of dict with keys: id, description, type, status, area_impacted
    
    Returns:
        Dict mapping issue ID to team name
    """
    if not issues:
        return {}
    
    result = {}
    
    # Check if Jira tickets table exists and has data
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jira_tickets WHERE embedding IS NOT NULL")
        jira_count = cursor.fetchone()[0]
        
        # If no embeddings yet, try simple text matching as fallback
        if jira_count == 0:
            print("No Jira embeddings found, using simple text matching fallback...")
            cursor.execute("SELECT COUNT(*) FROM jira_tickets WHERE team_name IS NOT NULL AND team_name != ''")
            simple_count = cursor.fetchone()[0]
            conn.close()
            
            if simple_count > 0:
                return analyze_team_simple_matching(issues)
            else:
                print("No Jira tickets found, falling back to Triage for all issues")
                return {issue.get("id", ""): "Triage" for issue in issues}
        
        conn.close()
            
    except Exception as e:
        print(f"Error checking Jira tickets: {e}, falling back to Triage")
        return {issue.get("id", ""): "Triage" for issue in issues}
    
    # Process each issue individually using the existing semantic matching
    for issue in issues:
        issue_id = issue.get("id", "")
        description = issue.get("description", "")
        issue_type = issue.get("type", "")
        status = issue.get("status", "")
        area_impacted = issue.get("area_impacted", "")
        
        team = analyze_team_assignment(description, issue_type, status, area_impacted)
        result[issue_id] = team
    
    return result

def ensure_jira_table_exists():
    """Ensure the Jira tickets table exists in the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create jira_tickets table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jira_tickets (
                id TEXT PRIMARY KEY,
                summary TEXT,
                description TEXT,
                resolution TEXT,
                assignee TEXT,
                team_name TEXT,
                embedding BLOB
            )
        """)
        
        conn.commit()
        conn.close()
        print("Jira tickets table initialized")
        
    except Exception as e:
        print(f"Error initializing Jira tickets table: {e}")

def analyze_team_simple_matching(issues: list) -> Dict[str, str]:
    """
    Simple text-based team matching as fallback when embeddings aren't ready.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all Jira tickets with teams
        cursor.execute("""
            SELECT id, summary, description, team_name 
            FROM jira_tickets 
            WHERE team_name IS NOT NULL AND team_name != ''
        """)
        jira_tickets = cursor.fetchall()
        conn.close()
        
        if not jira_tickets:
            return {issue.get("id", ""): "Triage" for issue in issues}
        
        result = {}
        
        for issue in issues:
            issue_id = issue.get("id", "")
            description = issue.get("description", "").lower()
            
            if not description:
                result[issue_id] = "Triage"
                continue
            
            # Simple keyword matching
            best_team = "Triage"
            max_matches = 0
            
            for jira_id, summary, jira_desc, team in jira_tickets:
                # Combine summary and description for matching
                jira_text = f"{summary or ''} {jira_desc or ''}".lower()
                
                # Count common words (simple matching)
                desc_words = set(description.split())
                jira_words = set(jira_text.split())
                
                # Remove common stop words
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
                desc_words -= stop_words
                jira_words -= stop_words
                
                # Count meaningful word matches
                matches = len(desc_words.intersection(jira_words))
                
                if matches > max_matches and matches >= 2:  # Require at least 2 word matches
                    max_matches = matches
                    best_team = team
            
            result[issue_id] = best_team
            if max_matches > 0:
                print(f"Simple match: {issue_id} -> {best_team} ({max_matches} word matches)")
        
        return result
        
    except Exception as e:
        print(f"Error in simple team matching: {e}")
        return {issue.get("id", ""): "Triage" for issue in issues}

# Initialize table on import
ensure_jira_table_exists()