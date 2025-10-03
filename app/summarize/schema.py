"""Summary schema definition - simple structure mirroring business rubric."""

from pydantic import BaseModel


class CallSummary(BaseModel):
    """Schema for call summaries with simple structure matching business rubric."""

    call_id: str
    
    # Mirror the rubric dimensions as simple fields
    call_resolution: str  # What customer wanted + resolution status
    action_items: str     # Next steps and follow-ups
    context_preservation: str  # Key business context and history
    compliance_notes: str  # Compliance issues and requirements
    quality_indicators: str  # Service quality and performance notes

    @classmethod
    def schema_text(cls) -> str:
        """Return schema as text for prompting."""
        return """
{
  "call_id": "string (from transcript)",
  "call_resolution": "string (what customer wanted and resolution status)",
  "action_items": "string (concrete next steps with ownership and deadlines)",
  "context_preservation": "string (key business context, customer history, account details)",
  "compliance_notes": "string (compliance issues, regulatory requirements, privacy concerns)",
  "quality_indicators": "string (service quality metrics, customer sentiment, performance notes)"
}
"""

    @classmethod
    def example_summary(cls) -> str:
        """Return an example of a perfect summary."""
        return """
EXAMPLE OF PERFECT BUSINESS SUMMARY:

Transcript: Customer calls about prescription refill, agent processes it, discusses insurance coverage, schedules follow-up

Perfect Summary:
{
  "call_id": "TRA-...",
  "call_resolution": "Customer requested refill for Metformin 500mg. Successfully processed refill at CVS Main Street location. Customer confirmed insurance coverage active. Refill will be ready in 2 hours. Customer expressed satisfaction with service.",
  "action_items": "1. Customer to pick up prescription at CVS Main Street by 3:00 PM today\n2. Pharmacy to send text notification when ready\n3. Agent to follow up with customer tomorrow to confirm pickup\n4. Update customer profile with preferred pharmacy location",
  "context_preservation": "Customer Sarah Johnson, Member ID M123456, DOB 03/15/1985. Previous calls about same medication. Insurance: Blue Cross Blue Shield, policy active. Preferred pharmacy: CVS Main Street. No previous issues with this medication.",
  "compliance_notes": "Standard prescription refill process followed. Insurance verification completed. No PHI concerns. Customer consented to text notifications. Call recorded for quality assurance.",
  "quality_indicators": "Call duration: 4 minutes 32 seconds. Customer sentiment: positive. Agent performance: efficient, knowledgeable. No escalations needed. Customer rated service 5/5. Process improvement: Consider proactive refill reminders for this customer."
}

This achieves 5/5 on all business dimensions because:
- Call Resolution: Clear what customer wanted + specific resolution details
- Action Items: Concrete steps with clear ownership and deadlines  
- Context Preservation: Complete business context for next agent
- Compliance Notes: All regulatory requirements documented
- Quality Indicators: Service metrics and performance notes captured
"""