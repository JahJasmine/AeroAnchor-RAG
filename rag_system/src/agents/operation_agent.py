from ..core.agent_base import BaseAgent
from ..prompts.operation_prompt import OPERATION_SYSTEM_PROMPT

class OperationAgent(BaseAgent):
    def __init__(self, rag_instances):
        super().__init__(
            name="operation_agent",
            rag_instances=rag_instances,
            system_prompt=OPERATION_SYSTEM_PROMPT
        )