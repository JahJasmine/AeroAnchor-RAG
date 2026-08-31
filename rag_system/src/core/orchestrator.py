# src/core/orchestrator.py
from typing import Dict, Any, List
import asyncio
from ..utils.logger import setup_logger
from .super_router import SuperRouter

logger = setup_logger(__name__)

class Orchestrator:
    """Orchestrator - coordinates the operation of the entire system"""

    def __init__(self, router: SuperRouter, agents: Dict[str, Any]):
        self.router = router
        self.agents = agents
        self.max_retries = 2
        logger.info("Orchestrator initialization complete")

    async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user query - with multiple fallbacks"""

        for attempt in range(self.max_retries):
            try:
                result = await self._process_query_once(query, context)

                # Check if successful
                if result.get('final_response') and 'failed' not in result.get('final_response', ''):
                    return result

                if attempt < self.max_retries - 1:
                    logger.warning(f"Attempt {attempt+1} failed, retrying...")
                    await asyncio.sleep(1)

            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt+1} timed out")
                if attempt >= self.max_retries - 1:
                    return self._create_fallback_response(query, context, "Request timed out")

            except Exception as e:
                logger.error(f"Attempt {attempt+1} raised an exception: {e}")
                if attempt >= self.max_retries - 1:
                    return self._create_fallback_response(query, context, str(e))

        return self._create_fallback_response(query, context, "All retries failed")

    def _create_fallback_response(self, query: str, context: Dict, error: str) -> Dict:
        """Create fallback response"""
        return {
            'query': query,
            'context': context,
            'final_response': f"""Sorry, the system is temporarily unable to process your request.

Error message: {error}

Suggestions:
1. Please try again later
2. Simplify your question
3. If the problem persists, please contact technical support""",
            'selected_agents': [],
            'error': error
        }

    async def _process_query_once(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a single query"""
        logger.info(f"Processing query: {query[:100]}...")

        # ========== 1. Routing decision ==========
        decision = await self.router.route(query, context)
        selected_agents = decision.get('selected_agents', [])

        # ========== 2. Ensure at least one agent ==========
        if not selected_agents:
            logger.warning("Router returned no agents, using hardcoded fallback")
            # Choose from available agents
            available = list(self.agents.keys())
            selected_agents = ['safety_agent'] if 'safety_agent' in available else available[:1]
            logger.info(f"Hardcoded fallback agents: {selected_agents}")

        # Filter out unavailable agents
        selected_agents = [a for a in selected_agents if a in self.agents and self.agents[a].enabled]
        if not selected_agents:
            logger.error("No available agents!")
            return {
                'query': query,
                'context': context,
                'final_response': 'The system has no available agents. Please check the system configuration.',
                'selected_agents': [],
                'error': 'No available agents'
            }

        # ========== 3. Call agents in parallel ==========
        agent_tasks = []
        for agent_name in selected_agents:
            if agent_name in self.agents and self.agents[agent_name].enabled:
                agent_tasks.append(
                    asyncio.wait_for(
                        self.agents[agent_name].process(query, context),
                        timeout=40.0
                    )
                )

        agent_responses = await asyncio.gather(*agent_tasks, return_exceptions=True)

        # ========== 4. Process responses ==========
        processed_responses = []
        for resp in agent_responses:
            if isinstance(resp, asyncio.TimeoutError):
                processed_responses.append({
                    'agent': 'unknown',
                    'status': 'error',
                    'error': 'Timeout'
                })
            elif isinstance(resp, Exception):
                processed_responses.append({
                    'agent': 'unknown',
                    'status': 'error',
                    'error': str(resp)
                })
            else:
                processed_responses.append(resp)

        # ========== 5. Check whether there are successful responses ==========
        success_count = sum(1 for r in processed_responses if r.get('status') == 'success')
        if success_count == 0:
            logger.warning("All agent calls failed")
            error_msgs = [r.get('error', 'Unknown') for r in processed_responses if r.get('error')]
            return {
                'query': query,
                'context': context,
                'router_decision': decision,
                'agent_responses': processed_responses,
                'final_response': f'All agents failed: {"; ".join(error_msgs[:2])}',
                'selected_agents': selected_agents,
                'error': 'All agents failed'
            }

        # ========== 6. Aggregate results ==========
        final_response = await self.router.aggregate(
            query, context, processed_responses
        )

        result = {
            'query': query,
            'context': context,
            'router_decision': decision,
            'agent_responses': processed_responses,
            'final_response': final_response,
            'selected_agents': selected_agents
        }

        logger.info(f"Query processing complete, used {len(selected_agents)} agents")
        return result
