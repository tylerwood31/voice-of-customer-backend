#!/usr/bin/env python3
"""
Robust semantic analysis system for team assignment and chat functionality
Handles both OpenAI embeddings and simple text fallback
"""
import sqlite3
import numpy as np
import pickle
import os
from typing import List, Tuple, Dict, Any, Optional
from config import DB_PATH, OPENAI_API_KEY

# OpenAI client setup with error handling
try:
    from openai import OpenAI
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
    else:
        openai_client = None
        OPENAI_AVAILABLE = False
        print("⚠️ OpenAI API key not configured")
except ImportError:
    openai_client = None
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI package not installed")

class SemanticAnalyzer:
    def __init__(self):
        self.db_path = DB_PATH
        
    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """Generate an embedding for the given text."""
        if not OPENAI_AVAILABLE or not text.strip():
            return None
        
        try:
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text.strip()
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            print(f"⚠️ Embedding generation failed: {e}")
            return None
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        try:
            return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        except:
            return 0.0
    
    def find_related_jira_tickets(self, question: str, top_n: int = 3) -> List[Tuple[float, str, str, str, str]]:
        """
        Find top N Jira tickets most similar to the question.
        Returns: List of (similarity, jira_id, summary, assignee, team_name)
        """
        if not question.strip():
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if we have Jira tickets with embeddings
            cursor.execute("""
                SELECT COUNT(*) FROM jira_tickets 
                WHERE embedding IS NOT NULL
            """)
            embedded_count = cursor.fetchone()[0]
            
            if embedded_count > 0 and OPENAI_AVAILABLE:
                # Use semantic similarity
                return self._semantic_jira_search(question, top_n, cursor)
            else:
                # Fall back to text search
                return self._text_jira_search(question, top_n, cursor)
                
        except Exception as e:
            print(f"⚠️ Jira search error: {e}")
            return []
        finally:
            try:
                conn.close()
            except:
                pass
    
    def _semantic_jira_search(self, question: str, top_n: int, cursor) -> List[Tuple[float, str, str, str, str]]:
        """Semantic search using embeddings"""
        try:
            query_embedding = self.embed_text(question)
            if query_embedding is None:
                return self._text_jira_search(question, top_n, cursor)
            
            cursor.execute("""
                SELECT id, summary, assignee, team_name, embedding
                FROM jira_tickets
                WHERE embedding IS NOT NULL
            """)
            jira_rows = cursor.fetchall()
            
            similarities = []
            for j_id, summary, assignee, team, emb_blob in jira_rows:
                try:
                    embedding = pickle.loads(emb_blob)
                    similarity = self.cosine_similarity(query_embedding, embedding)
                    similarities.append((similarity, j_id, summary or "", assignee or "", team or ""))
                except Exception as e:
                    continue
            
            similarities.sort(reverse=True, key=lambda x: x[0])
            return similarities[:top_n]
            
        except Exception as e:
            print(f"⚠️ Semantic search failed, falling back to text search: {e}")
            return self._text_jira_search(question, top_n, cursor)
    
    def _text_jira_search(self, question: str, top_n: int, cursor) -> List[Tuple[float, str, str, str, str]]:
        """Simple text-based search fallback"""
        try:
            # Simple keyword matching
            keywords = question.lower().split()
            
            cursor.execute("""
                SELECT id, summary, description, assignee, team_name
                FROM jira_tickets
                WHERE team_name IS NOT NULL AND team_name != ''
            """)
            jira_rows = cursor.fetchall()
            
            matches = []
            for j_id, summary, description, assignee, team in jira_rows:
                # Combine summary and description for matching
                text = f"{summary or ''} {description or ''}".lower()
                
                # Count keyword matches
                score = 0
                for keyword in keywords:
                    if len(keyword) > 2:  # Ignore very short words
                        score += text.count(keyword)
                
                if score > 0:
                    # Normalize score (0-1 range to match semantic similarity)
                    normalized_score = min(score / 10.0, 1.0)
                    matches.append((normalized_score, j_id, summary or "", assignee or "", team or ""))
            
            matches.sort(reverse=True, key=lambda x: x[0])
            return matches[:top_n]
            
        except Exception as e:
            print(f"⚠️ Text search failed: {e}")
            return []
    
    def find_related_feedback(self, question: str, top_n: int = 5) -> List[Tuple[float, str, str, str, str]]:
        """
        Find top N feedback items most similar to the question.
        Returns: List of (similarity, feedback_id, description, priority, team)
        """
        if not question.strip():
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # For now, use simple text search for feedback
            # TODO: Add embedding support for feedback if needed
            return self._text_feedback_search(question, top_n, cursor)
            
        except Exception as e:
            print(f"⚠️ Feedback search error: {e}")
            return []
        finally:
            try:
                conn.close()
            except:
                pass
    
    def _text_feedback_search(self, question: str, top_n: int, cursor) -> List[Tuple[float, str, str, str, str]]:
        """Simple text-based feedback search"""
        try:
            keywords = question.lower().split()
            
            cursor.execute("""
                SELECT id, initial_description, notes, priority, team_routed
                FROM feedback
                WHERE initial_description IS NOT NULL OR notes IS NOT NULL
            """)
            feedback_rows = cursor.fetchall()
            
            matches = []
            for f_id, initial_desc, notes, priority, team in feedback_rows:
                # Combine description and notes for matching
                text = f"{initial_desc or ''} {notes or ''}".lower()
                
                # Count keyword matches
                score = 0
                for keyword in keywords:
                    if len(keyword) > 2:
                        score += text.count(keyword)
                
                if score > 0:
                    normalized_score = min(score / 5.0, 1.0)
                    description = initial_desc or notes or "No description"
                    matches.append((normalized_score, f_id, description, priority or "", team or ""))
            
            matches.sort(reverse=True, key=lambda x: x[0])
            return matches[:top_n]
            
        except Exception as e:
            print(f"⚠️ Feedback text search failed: {e}")
            return []
    
    def vectorize_jira_tickets(self, batch_size: int = 50):
        """Vectorize Jira tickets that don't have embeddings yet"""
        if not OPENAI_AVAILABLE:
            print("⚠️ OpenAI not available, skipping vectorization")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find tickets without embeddings
            cursor.execute("""
                SELECT id, summary, description FROM jira_tickets 
                WHERE embedding IS NULL AND (summary IS NOT NULL OR description IS NOT NULL)
            """)
            tickets = cursor.fetchall()
            
            if not tickets:
                print("✅ All Jira tickets already vectorized")
                return True
            
            print(f"🔄 Vectorizing {len(tickets)} Jira tickets...")
            
            vectorized_count = 0
            for i, (ticket_id, summary, description) in enumerate(tickets):
                # Create text for embedding
                text = f"{summary or ''} {description or ''}".strip()
                if not text:
                    continue
                
                # Generate embedding
                embedding = self.embed_text(text)
                if embedding is not None:
                    # Store embedding
                    cursor.execute(
                        "UPDATE jira_tickets SET embedding = ? WHERE id = ?",
                        (pickle.dumps(embedding), ticket_id)
                    )
                    vectorized_count += 1
                    
                    if vectorized_count % 10 == 0:
                        print(f"📊 Vectorized {vectorized_count}/{len(tickets)} tickets")
                        conn.commit()
                
                # Batch processing to avoid overwhelming API
                if (i + 1) % batch_size == 0:
                    conn.commit()
                    print(f"💾 Committed batch of {batch_size}")
            
            conn.commit()
            conn.close()
            
            print(f"✅ Vectorization completed: {vectorized_count} tickets processed")
            return True
            
        except Exception as e:
            print(f"❌ Vectorization failed: {e}")
            return False
    
    def get_vectorization_status(self) -> Dict[str, Any]:
        """Get status of Jira ticket vectorization"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM jira_tickets")
            total_tickets = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM jira_tickets WHERE embedding IS NOT NULL")
            vectorized_tickets = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_tickets": total_tickets,
                "vectorized_tickets": vectorized_tickets,
                "vectorization_percentage": round((vectorized_tickets / total_tickets) * 100, 1) if total_tickets > 0 else 0,
                "openai_available": OPENAI_AVAILABLE,
                "ready_for_semantic_search": vectorized_tickets > 0 and OPENAI_AVAILABLE
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def assign_teams_to_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Assign teams to issues based on semantic similarity to Jira tickets.
        
        Args:
            issues: List of issue dictionaries with keys: id, description, type, status, area_impacted
            
        Returns:
            Dict mapping issue IDs to team names
        """
        team_assignments = {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all Jira tickets with team information
            cursor.execute("""
                SELECT id, summary, description, team_name, embedding
                FROM jira_tickets 
                WHERE team_name IS NOT NULL AND team_name != ''
            """)
            jira_rows = cursor.fetchall()
            
            if not jira_rows:
                print("⚠️ No Jira tickets with team information found")
                # Fallback to area-based assignment
                return self._assign_teams_by_area(issues)
            
            # Process each issue
            for issue in issues:
                issue_id = issue.get("id", "")
                description = issue.get("description", "")
                area_impacted = issue.get("area_impacted", "")
                issue_type = issue.get("type", "")
                
                # Create search text from issue
                search_text = f"{description} {area_impacted} {issue_type}".strip()
                
                if not search_text:
                    team_assignments[issue_id] = "Triage"
                    continue
                
                # Try semantic search if OpenAI is available
                best_team = "Triage"
                if OPENAI_AVAILABLE:
                    issue_embedding = self.embed_text(search_text)
                    if issue_embedding is not None:
                        best_similarity = 0.0
                        
                        for j_id, summary, jira_desc, team_name, emb_blob in jira_rows:
                            if emb_blob:
                                try:
                                    jira_embedding = pickle.loads(emb_blob)
                                    similarity = self.cosine_similarity(issue_embedding, jira_embedding)
                                    
                                    if similarity > best_similarity:
                                        best_similarity = similarity
                                        best_team = team_name
                                        
                                except Exception:
                                    continue
                        
                        # Only use semantic result if similarity is reasonable
                        if best_similarity < 0.3:
                            best_team = self._assign_team_by_area(area_impacted)
                    else:
                        best_team = self._assign_team_by_area(area_impacted)
                else:
                    # Fallback to text-based matching
                    best_team = self._assign_team_by_text_similarity(search_text, jira_rows, area_impacted)
                
                team_assignments[issue_id] = best_team
            
            conn.close()
            return team_assignments
            
        except Exception as e:
            print(f"⚠️ Team assignment failed: {e}")
            # Fallback to area-based assignment
            return self._assign_teams_by_area(issues)
    
    def _assign_teams_by_area(self, issues: List[Dict[str, Any]]) -> Dict[str, str]:
        """Fallback team assignment based on area impacted."""
        assignments = {}
        for issue in issues:
            issue_id = issue.get("id", "")
            area_impacted = issue.get("area_impacted", "")
            assignments[issue_id] = self._assign_team_by_area(area_impacted)
        return assignments
    
    def _assign_team_by_area(self, area_impacted: str) -> str:
        """Assign team based on area impacted."""
        if not area_impacted:
            return "Triage"
        
        area_lower = area_impacted.lower()
        if "salesforce" in area_lower:
            return "Salesforce Team"
        elif "billing" in area_lower or "payment" in area_lower:
            return "Billing Team"
        elif "underwriting" in area_lower:
            return "Underwriting Team"
        elif "claims" in area_lower:
            return "Claims Team"
        elif "portal" in area_lower or "dashboard" in area_lower:
            return "Portal Team"
        else:
            return "Triage"
    
    def _assign_team_by_text_similarity(self, search_text: str, jira_rows: List, area_impacted: str) -> str:
        """Assign team using text-based similarity matching."""
        best_score = 0
        best_team = self._assign_team_by_area(area_impacted)
        
        search_words = set(search_text.lower().split())
        
        for j_id, summary, jira_desc, team_name, emb_blob in jira_rows:
            jira_text = f"{summary or ''} {jira_desc or ''}".lower()
            jira_words = set(jira_text.split())
            
            # Calculate word overlap score
            common_words = search_words.intersection(jira_words)
            if common_words:
                score = len(common_words) / len(search_words.union(jira_words))
                if score > best_score:
                    best_score = score
                    best_team = team_name
        
        return best_team if best_score > 0.1 else self._assign_team_by_area(area_impacted)

# Global semantic analyzer instance
semantic_analyzer = SemanticAnalyzer()

# Legacy function names for backward compatibility
def find_related_tickets(question: str, top_n: int = 3):
    """Legacy function for backward compatibility"""
    return semantic_analyzer.find_related_jira_tickets(question, top_n)

def find_related_feedback(question: str, top_n: int = 5):
    """Legacy function for backward compatibility"""
    return semantic_analyzer.find_related_feedback(question, top_n)