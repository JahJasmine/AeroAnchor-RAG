from ..core.agent_base import BaseAgent
from ..prompts.compliance_prompt import COMPLIANCE_SYSTEM_PROMPT

class ComplianceAgent(BaseAgent):
    def __init__(self, rag_instances):
        super().__init__(
            name="compliance_agent",
            rag_instances=rag_instances,
            system_prompt=COMPLIANCE_SYSTEM_PROMPT
        )