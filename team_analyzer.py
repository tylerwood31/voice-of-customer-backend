"""
Robust team assignment using Jira ticket similarity analysis
"""
import os
import sys
from typing import Dict, Any, List
import sqlite3
from config import DB_PATH, OPENAI_API_KEY

# Import our robust semantic analyzer
from semantic_analyzer import semantic_analyzer

# OpenAI setup for enhanced analysis
try:
    from openai import OpenAI
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
    else:
        openai_client = None
        OPENAI_AVAILABLE = False
except ImportError:
    openai_client = None
    OPENAI_AVAILABLE = False

def analyze_team_assignment(issue_description: str, issue_type: str = "", status: str = "", area_impacted: str = "") -> str:
    """
    Analyze team assignment using multiple strategies:
    1. Jira ticket similarity (semantic or text-based)
    2. OpenAI-enhanced analysis for edge cases
    3. Rule-based fallback
    
    Args:
        issue_description: The main description/notes of the issue
        issue_type: Type of issue (if available)
        status: Current status (if available) 
        area_impacted: Area/system impacted (if available)
    
    Returns:
        Team name as string
    """
    if not issue_description or not issue_description.strip():
        return "Triage"
    
    try:
        # Step 1: Find similar Jira tickets using our robust semantic analyzer
        jira_matches = semantic_analyzer.find_related_jira_tickets(issue_description, top_n=3)
        
        if jira_matches:
            # Analyze the matches for team assignment
            best_match = jira_matches[0]
            similarity, jira_id, jira_summary, assignee, team_name = best_match
            
            # High confidence match
            if similarity > 0.7 and team_name:
                print(f"🎯 High confidence match: {jira_id} (similarity: {similarity:.3f}) -> {team_name}")
                return team_name
            
            # Medium confidence - use weighted voting
            elif similarity > 0.4:
                team_votes = {}
                for sim, j_id, j_sum, j_assignee, j_team in jira_matches:
                    if sim > 0.3 and j_team:
                        team_votes[j_team] = team_votes.get(j_team, 0) + sim
                
                if team_votes:
                    best_team = max(team_votes.items(), key=lambda x: x[1])
                    print(f"📊 Team consensus: {best_team[0]} (weighted score: {best_team[1]:.3f})")
                    return best_team[0]
        
        # Step 2: If Jira matching is inconclusive, use OpenAI for enhanced analysis
        if OPENAI_AVAILABLE:
            openai_team = analyze_with_openai(issue_description, issue_type, status, area_impacted)
            if openai_team != "Triage":
                print(f"🤖 OpenAI assignment: {openai_team}")
                return openai_team
        
        # Step 3: Rule-based fallback
        rule_based_team = analyze_with_rules(issue_description, issue_type, status, area_impacted)
        print(f"📋 Rule-based assignment: {rule_based_team}")
        return rule_based_team
        
    except Exception as e:
        print(f"❌ Team analysis error: {e}")
        return "Triage"

def analyze_with_openai(description: str, issue_type: str, status: str, area_impacted: str) -> str:
    """Use OpenAI to analyze team assignment when Jira matching is inconclusive"""
    if not OPENAI_AVAILABLE:
        return "Triage"
    
    try:
        context = f"""
        Issue Description: {description}
        Type: {issue_type}
        Status: {status}
        Area Impacted: {area_impacted}
        """
        
        prompt = f"""
        You are a technical support specialist for CoverWallet, an insurance technology company.
        
        Analyze this customer issue and assign it to the most appropriate team:
        
        **Engineering** - Technical bugs, system errors, API issues, performance problems, code defects
        **Product** - Feature requests, UX issues, workflow problems, business logic concerns
        **Support** - Training questions, user education, account access, how-to questions
        **Sales** - Pricing questions, quote issues, sales process, new business inquiries
        **Billing Integrations** - Payment processing, billing systems, invoice issues
        **Policies** - Policy management, underwriting, coverage questions
        **Quote** - Quote generation, rating, pricing calculations
        **Data Platform** - Data processing, analytics, reporting issues
        **Triage** - Unclear issues that need investigation
        
        Issue details:
        {context}
        
        Respond with ONLY the team name. No explanation.
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1
        )
        
        team = response.choices[0].message.content.strip()
        
        # Validate response
        valid_teams = [
            "Engineering", "Product", "Support", "Sales", "Billing Integrations",
            "Policies", "Quote", "Data Platform", "Triage"
        ]
        
        return team if team in valid_teams else "Triage"
        
    except Exception as e:
        print(f"⚠️ OpenAI analysis failed: {e}")
        return "Triage"

def analyze_with_rules(description: str, issue_type: str, status: str, area_impacted: str) -> str:
    """Rule-based team assignment as final fallback"""
    desc_lower = description.lower()
    
    # Engineering keywords
    if any(word in desc_lower for word in ['error', 'bug', 'crash', 'broken', 'fail', 'exception', 'timeout']):
        return "Engineering"
    
    # Support keywords
    if any(word in desc_lower for word in ['how to', 'training', 'help', 'tutorial', 'guide']):
        return "Support"
    
    # Sales keywords
    if any(word in desc_lower for word in ['price', 'quote', 'sales', 'cost', 'purchase']):
        return "Sales"
    
    # Product keywords
    if any(word in desc_lower for word in ['feature', 'request', 'enhance', 'improve', 'suggestion']):
        return "Product"
    
    # Default
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

def analyze_team_assignment_simple(description: str, issue_type: str = "", status: str = "", area_impacted: str = "") -> str:
    """
    Simple single-issue team assignment using text matching.
    """
    issues = [{
        "id": "temp",
        "description": description,
        "type": issue_type,
        "status": status,
        "area_impacted": area_impacted
    }]
    
    result = analyze_team_simple_matching(issues)
    return result.get("temp", "Triage")

# Initialize table on import
ensure_jira_table_exists()