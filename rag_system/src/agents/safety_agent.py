from ..core.agent_base import BaseAgent
from ..prompts.safety_prompt import SAFETY_SYSTEM_PROMPT

class SafetyAgent(BaseAgent):
    def __init__(self, rag_instances):
        super().__init__(
            name="safety_agent",
            rag_instances=rag_instances,
            system_prompt=SAFETY_SYSTEM_PROMPT
        )