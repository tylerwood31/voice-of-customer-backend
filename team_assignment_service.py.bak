"""
Team Assignment Service

Reads team_directory.csv and provides intelligent team assignment
based on area impacted and semantic matching.
"""

import csv
import os
from typing import Dict, List, Optional
from difflib import SequenceMatcher

class TeamAssignmentService:
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            # Default path to team_directory.csv
            csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'team_directory.csv')
        
        self.csv_path = csv_path
        self.teams = self._load_teams()
        
    def _load_teams(self) -> List[Dict[str, str]]:
        """Load teams from CSV file"""
        teams = []
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row.get('Team'):  # Only include rows with team names
                        teams.append({
                            'name': row['Team'].strip(),
                            'tech_rep': row.get('Tech Rep / Dev', '').strip(),
                            'manager': row.get('Tem Manager', '').strip(),
                            'product_manager': row.get('Product Manager', '').strip()
                        })
        except FileNotFoundError:
            print(f"Warning: Team directory CSV not found at {self.csv_path}")
        except Exception as e:
            print(f"Error loading team directory: {e}")
        
        return teams
    
    def _similarity_score(self, text1: str, text2: str) -> float:
        """Calculate similarity between two strings"""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _contains_keywords(self, area_impacted: str, team_name: str) -> bool:
        """Check if area contains keywords related to team"""
        if not area_impacted or not team_name:
            return False
            
        area_lower = area_impacted.lower()
        team_lower = team_name.lower()
        
        # Direct keyword matching
        keyword_matches = {
            'salesforce': ['crm sf', 'salesforce'],
            'portal': ['client portal', 'agent portal', 'portal'],
            'billing': ['billing', 'payment', 'digital payments'],
            'quotes': ['quotes', 'quote'],
            'application': ['application'],
            'policies': ['policies', 'policy'],
            'documents': ['documents', 'document'],
            'workflows': ['workflows', 'workflow'],
            'onboarding': ['onboarding', 'user onboarding'],
            'data': ['data'],
            'iam': ['iam', 'identity', 'access management'],
            'affinities': ['affinities', 'us affinities'],
            'integrations': ['integration', 'market integrations', 'billing integrations'],
            'orchestration': ['orchestration', 'connect 3rd party'],
            'checkout': ['checkout']
        }
        
        # Check for keyword matches
        for keyword, variations in keyword_matches.items():
            if keyword in team_lower:
                for variation in variations:
                    if variation in area_lower:
                        return True
        
        # Check if any significant words from team name appear in area
        team_words = [word for word in team_lower.split() if len(word) > 3]
        for word in team_words:
            if word in area_lower:
                return True
                
        return False
    
    def assign_team(self, area_impacted: str, description: str = "", type_of_issue: str = "") -> str:
        """
        Assign team based on area impacted and other contextual information
        
        Args:
            area_impacted: The system/area that was impacted
            description: Issue description for additional context
            type_of_issue: Type of issue for additional context
            
        Returns:
            Team name or "Unassigned" if no match found
        """
        if not area_impacted or area_impacted.lower() in ['unknown', 'n/a', '']:
            return "Unassigned"
        
        best_match = None
        best_score = 0.0
        
        # Combine all text for context
        full_text = f"{area_impacted} {description} {type_of_issue}".lower()
        
        for team in self.teams:
            team_name = team['name']
            
            # Check for keyword matches first (highest priority)
            if self._contains_keywords(area_impacted, team_name):
                return team_name
            
            # Calculate similarity score
            similarity = self._similarity_score(area_impacted, team_name)
            
            # Boost score if team name appears in full context
            if team_name.lower() in full_text:
                similarity += 0.3
                
            # Check for partial word matches
            team_words = set(team_name.lower().split())
            area_words = set(area_impacted.lower().split())
            if team_words.intersection(area_words):
                similarity += 0.2
            
            if similarity > best_score:
                best_score = similarity
                best_match = team_name
        
        # Only return match if confidence is high enough
        if best_score >= 0.4:
            return best_match
        
        return "Unassigned"
    
    def get_all_teams(self) -> List[str]:
        """Get list of all team names"""
        return [team['name'] for team in self.teams]
    
    def get_team_info(self, team_name: str) -> Optional[Dict[str, str]]:
        """Get detailed information about a specific team"""
        for team in self.teams:
            if team['name'].lower() == team_name.lower():
                return team
        return None

# Global instance
team_service = TeamAssignmentService()