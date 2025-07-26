from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import os
from openai import OpenAI

router = APIRouter()

# Initialize OpenAI client
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class IssueData(BaseModel):
    id: str
    created: str
    description: str
    environment: str
    system: str
    team: str

class SummaryRequest(BaseModel):
    issues: List[IssueData]

@router.post("/generate", summary="Generate AI summary of filtered issues")
async def generate_ai_summary(request: SummaryRequest):
    """Generate an AI-powered summary of customer feedback issues."""
    
    if not request.issues:
        return {"summary": "No issues to analyze."}
    
    # Create a readable list of issues for context
    issues_list = "\n".join([
        f"- [{issue.created}] ({issue.team}) {issue.environment}/{issue.system}: {issue.description[:200]}..."
        for issue in request.issues
    ])
    
    prompt = f"""
You are an expert product manager and customer feedback analyst.
Analyze the customer issues and feedback below and produce a concise, structured summary.

**Your output format should be:**
**Executive Summary**
[2–3 sentences summarizing the major themes or patterns.]

**Key Actionable Insights**
1. [Direct, actionable insight with context, focused on recurring issues or trends.]
2. [Another actionable recommendation.]
3. [Another actionable recommendation.]
4. [Another actionable recommendation.]
5. [Another actionable recommendation.]

**High-Risk/High-Priority Areas**
• [Component or system that appears critical or recurring in the issues, with reason.]
• [Another high-risk component or integration.]

**Opportunities to Improve Communication or Workflows**
• [Recommendation to improve feedback channels, user support, or internal processes.]
• [Another recommendation.]
• [Another recommendation.]

**Do not use filler or unnecessary commentary.** Focus only on what the data shows. Dive directly into the issues and feedback trends, using straightforward and specific language.

Dataset ({len(request.issues)} issues):
{issues_list}
"""
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        return {"summary": summary}
        
    except Exception as error:
        print(f"Error generating AI summary: {error}")
        raise HTTPException(status_code=500, detail="Error generating AI summary")