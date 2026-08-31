from ..core.agent_base import BaseAgent
from ..prompts.student_prompt import STUDENT_SYSTEM_PROMPT

class StudentAgent(BaseAgent):
    def __init__(self, rag_instances):
        super().__init__(
            name="student_agent",
            rag_instances=rag_instances,
            system_prompt=STUDENT_SYSTEM_PROMPT
        )