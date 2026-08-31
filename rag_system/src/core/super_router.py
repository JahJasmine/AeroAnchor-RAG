# src/core/super_router.py
import json
import re
from typing import List, Dict, Any, Optional
import asyncio
from ..utils.llm_client import llm_client
from ..utils.logger import setup_logger
from ..prompts.router_prompt import ROUTER_SYSTEM_PROMPT, ROUTER_AGGREGATE_PROMPT

logger = setup_logger(__name__)

class SuperRouter:
    """Super Router - intent recognition and agent routing"""

    def __init__(self, agents: Dict[str, Any]):
        self.agents = agents
        self.enabled_agents = {name: agent for name, agent in agents.items() if agent.enabled}
        logger.info(f"SuperRouter initialized, available agents: {list(self.enabled_agents.keys())}")

    def _get_fallback_agents(self, query: str) -> List[str]:
        """Intelligently select fallback agents based on query content"""
        query_lower = query.lower()
        fallback = []

        # Always include the safety agent
        if 'safety_agent' in self.enabled_agents:
            fallback.append('safety_agent')

        # If it involves operations/procedures, add operation_agent
        op_keywords = ['procedure', 'step', 'sequence', 'operate', 'control', 'push', 'pull',
                       'takeoff', 'landing', 'climb', 'descent', 'approach', 'taxi',
                       'checklist', 'do', 'should', 'how to']
        if any(kw in query_lower for kw in op_keywords):
            if 'operation_agent' in self.enabled_agents and 'operation_agent' not in fallback:
                fallback.append('operation_agent')

        # If it involves regulations/standards, add compliance_agent
        reg_keywords = ['regulation', 'rule', 'require', 'compliance', 'annex',
                        'cfr', 'far', 'icao', 'standard', 'manual', 'sop']
        if any(kw in query_lower for kw in reg_keywords):
            if 'compliance_agent' in self.enabled_agents and 'compliance_agent' not in fallback:
                fallback.append('compliance_agent')

        # If it involves components, add interact_agent
        part_keywords = ['part', 'component', 'wing', 'tail', 'engine', 'fuselage',
                         'elevator', 'aileron', 'rudder', 'flap', 'landing gear']
        if any(kw in query_lower for kw in part_keywords):
            if 'interact_agent' in self.enabled_agents and 'interact_agent' not in fallback:
                fallback.append('interact_agent')

        # If it involves students/training, add student_agent
        student_keywords = ['student', 'training', 'evaluate', 'learn', 'teach',
                            'instructor', 'pilot', 'experience', 'skill']
        if any(kw in query_lower for kw in student_keywords):
            if 'student_agent' in self.enabled_agents and 'student_agent' not in fallback:
                fallback.append('student_agent')

        # Fallback: at least two agents
        if len(fallback) == 1 and 'operation_agent' in self.enabled_agents:
            fallback.append('operation_agent')
        elif len(fallback) == 0:
            # Final fallback
            fallback = ['safety_agent', 'operation_agent']

        # Filter to ensure all agents exist
        return [a for a in fallback if a in self.enabled_agents]

    async def route(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Routing decision - multiple fallbacks"""

        # ========== Step 1: try LLM routing ==========
        try:
            messages = [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": f"""
User Query: {query}
Context: {context or {}}

Please analyze the intent and select the appropriate Agent combination.
IMPORTANT: You MUST select at least one agent. The available agents are: {list(self.enabled_agents.keys())}
Return ONLY valid JSON.
"""}
            ]

            response = await llm_client.chat_completion(
                messages,
                response_format={"type": "json_object"}
            )

            decision = await llm_client.extract_json(response)
            selected = decision.get('selected_agents', [])

            # Verify that the selected agents exist and are enabled
            valid_agents = [a for a in selected if a in self.enabled_agents]

            if valid_agents:
                logger.info(f"LLM routing successful: {valid_agents}")
                return {
                    'intent': decision.get('intent', 'unknown'),
                    'selected_agents': valid_agents,
                    'reasoning': decision.get('reasoning', 'LLM routing')
                }
            else:
                logger.warning(f"LLM routing returned invalid agents: {selected}")

        except Exception as e:
            logger.error(f"LLM routing failed: {str(e)}")

        # ========== Step 2: intelligent fallback routing ==========
        logger.info(f"Using intelligent fallback routing")
        fallback_agents = self._get_fallback_agents(query)
        logger.info(f"Fallback routing selection: {fallback_agents}")

        return {
            'intent': 'fallback_route',
            'selected_agents': fallback_agents,
            'reasoning': 'Intelligent fallback routing (based on query keywords)'
        }

    async def aggregate(self, query: str, context: Dict[str, Any],
                       agent_responses: List[Dict]) -> str:
        """Aggregate responses from multiple agents - with fallback"""
        try:
            # Check for safety warnings
            safety_response = None
            for resp in agent_responses:
                if resp.get('agent') == 'safety_agent' and resp.get('status') == 'success':
                    safety_response = resp.get('response', '')
                    if '🚨' in safety_response or '⚠️' in safety_response:
                        logger.warning(f"Safety agent issued a warning")

            # Filter valid responses
            valid_responses = []
            for r in agent_responses:
                if r.get('status') == 'success' and r.get('response'):
                    valid_responses.append(r)
                elif r.get('status') == 'error':
                    logger.warning(f"Agent {r.get('agent', 'unknown')} returned an error: {r.get('error', '')}")

            # ========== If there are no valid responses, generate a fallback answer ==========
            if not valid_responses:
                logger.warning("All agent responses failed, generating fallback answer")

                # Try to extract useful information from errors
                error_msgs = []
                for r in agent_responses:
                    if r.get('status') == 'error':
                        error_msgs.append(r.get('error', ''))

                if error_msgs:
                    return f"""Sorry, the system cannot fully process your request at this time.

Diagnostic Information:
- All agents failed to respond
- Errors: {'; '.join(error_msgs[:2])}

Suggestions:
1. Please try again later
2. Simplify your question
3. If the problem persists, please check the system logs"""

                return """Sorry, the system cannot process your request at this time. Please try again later.

Tips:
1. Make sure your question is clear and specific
2. Try rephrasing your question
3. If your question involves specific numbers or regulations, please provide more context"""

            # Build aggregation message
            responses_text = ""
            for resp in valid_responses:
                responses_text += f"\n## {resp.get('agent')} Response:\n{resp.get('response')}\n"

            messages = [
                {"role": "system", "content": ROUTER_AGGREGATE_PROMPT},
                {"role": "user", "content": f"""
User Query: {query}
Context: {context or {}}

Agent Responses:
{responses_text}

Please synthesize the above responses into a final answer.
"""}
            ]

            if safety_response and ('🚨' in safety_response or '⚠️' in safety_response):
                messages[1]['content'] += f"\n\n**Safety Warning (Highest Priority)**:\n{safety_response}"

            final_response = await llm_client.chat_completion(messages)

            logger.info("Aggregation complete")
            return final_response

        except Exception as e:
            logger.error(f"Aggregation failed: {str(e)}")
            # Fallback: if there are valid responses, return the first one
            for resp in agent_responses:
                if resp.get('status') == 'success' and resp.get('response'):
                    return resp.get('response')
            return "Aggregation failed, please try again later."
