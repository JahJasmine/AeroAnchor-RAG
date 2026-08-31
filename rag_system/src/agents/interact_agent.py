from ..core.agent_base import BaseAgent
from ..prompts.interact_prompt import INTERACT_SYSTEM_PROMPT

class InteractAgent(BaseAgent):
    def __init__(self, rag_instances):
        super().__init__(
            name="interact_agent",
            rag_instances=rag_instances,
            system_prompt=INTERACT_SYSTEM_PROMPT
        )