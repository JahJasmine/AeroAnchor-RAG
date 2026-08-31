# src/api/app.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
from ..core.orchestrator import Orchestrator
from ..core.agent_base import BaseAgent
from ..utils.logger import setup_logger
from ..utils.config import config

logger = setup_logger(__name__)

app = FastAPI(title="Aviation Teaching Multi-Agent RAG System", version="2.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
orchestrator = None
agents = {}
rag_instances = {}

class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = {}
    aircraft_type: Optional[str] = "c172p"  # default aircraft type

class QueryResponse(BaseModel):
    query: str
    context: Optional[Dict[str, Any]]
    final_response: str
    router_decision: Optional[Dict[str, Any]]
    agent_responses: Optional[List[Dict[str, Any]]]
    selected_agents: Optional[List[str]]
    aircraft_type: Optional[str]

class FeedbackRequest(BaseModel):
    query: str
    response: str
    rating: int
    comment: Optional[str] = ""

@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup"""
    global orchestrator, agents, rag_instances

    from ..rag.rag_builder import RAGBuilder
    rag_builder = RAGBuilder()

    # Build the general RAG instances first
    rag_instances = rag_builder.build_all(load_documents=True, aircraft_type="general")

    # If an aircraft type is specified, also build aircraft-specific RAG
    aircraft_types = config.get('aircraft_types', ['c172p'])
    for atype in aircraft_types:
        try:
            atype_instances = rag_builder.build_for_aircraft(atype)
            rag_instances.update(atype_instances)
        except Exception as e:
            logger.error(f"Failed to build RAG for aircraft type {atype}: {str(e)}")

    # Create agents (using the general RAG instances)
    from ..agents import (
        SafetyAgent, OperationAgent, ComplianceAgent,
        StudentAgent, InteractAgent
    )

    agent_configs = config.get('agents', {})

    # Get RAG instances
    def get_rag_instances(names):
        return [rag_instances[name] for name in names if name in rag_instances]

    agents['safety_agent'] = SafetyAgent(
        get_rag_instances(['rag_aircraft_params', 'rag_performance', 'rag_emergency'])
    )
    agents['safety_agent'].enabled = agent_configs.get('safety_agent', {}).get('enabled', True)

    agents['operation_agent'] = OperationAgent(
        get_rag_instances(['rag_checklists', 'rag_manipulation', 'rag_general'])
    )
    agents['operation_agent'].enabled = agent_configs.get('operation_agent', {}).get('enabled', True)

    agents['compliance_agent'] = ComplianceAgent(
        get_rag_instances(['rag_checklists', 'rag_regulations', 'rag_acs'])
    )
    agents['compliance_agent'].enabled = agent_configs.get('compliance_agent', {}).get('enabled', True)

    agents['student_agent'] = StudentAgent(
        get_rag_instances(['rag_acs', 'rag_general'])
    )
    agents['student_agent'].enabled = agent_configs.get('student_agent', {}).get('enabled', True)

    agents['interact_agent'] = InteractAgent(
        get_rag_instances(['rag_components', 'rag_manipulation'])
    )
    agents['interact_agent'].enabled = agent_configs.get('interact_agent', {}).get('enabled', True)

    from ..core.super_router import SuperRouter
    router = SuperRouter(agents)
    orchestrator = Orchestrator(router, agents)

    logger.info("System initialization complete")

@app.get("/")
async def root():
    return {"message": "Aviation Teaching Multi-Agent RAG System", "status": "running"}

@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Main query endpoint - supports multiple aircraft types"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")

    try:
        # Add aircraft type to context
        context = request.context or {}
        context['aircraft_type'] = request.aircraft_type

        result = await orchestrator.process_query(
            request.query,
            context
        )

        return QueryResponse(
            query=request.query,
            context=context,
            final_response=result.get('final_response', ''),
            router_decision=result.get('router_decision'),
            agent_responses=result.get('agent_responses'),
            selected_agents=result.get('selected_agents'),
            aircraft_type=request.aircraft_type
        )
    except Exception as e:
        logger.error(f"API query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/aircraft")
async def list_aircraft():
    """List available aircraft types"""
    aircraft_types = config.get('aircraft_types', ['c172p'])
    return {
        'aircraft_types': aircraft_types,
        'default': 'c172p'
    }

@app.get("/api/agents")
async def list_agents():
    """List all agents and their status"""
    if not agents:
        raise HTTPException(status_code=503, detail="System not initialized")

    agent_list = []
    for name, agent in agents.items():
        agent_list.append({
            'name': name,
            'enabled': agent.enabled,
            'rag_instances': list(agent.rag_instances.keys()),
            'status': 'active' if agent.enabled else 'disabled'
        })

    return {
        'agents': agent_list,
        'total': len(agent_list),
        'enabled': sum(1 for a in agent_list if a['enabled'])
    }

@app.get("/api/rag/status")
async def get_rag_status(aircraft_type: Optional[str] = None):
    """List the status of all RAG instances"""
    if not rag_instances:
        raise HTTPException(status_code=503, detail="System not initialized")

    # Filter by aircraft type
    status_list = []
    for name, instance in rag_instances.items():
        if aircraft_type and instance.aircraft_type != aircraft_type:
            continue
        status_list.append(instance.get_status())

    return {
        'rag_instances': status_list,
        'total': len(status_list)
    }

@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """User feedback endpoint"""
    logger.info(f"Received feedback - query: {request.query[:50]}..., rating: {request.rating}")

    import json
    from pathlib import Path
    feedback_file = Path(__file__).parent.parent.parent / "data" / "feedback.jsonl"
    feedback_file.parent.mkdir(parents=True, exist_ok=True)

    with open(feedback_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(request.dict(), ensure_ascii=False) + '\n')

    return {
        'status': 'success',
        'message': 'Feedback received, thank you for your review!'
    }

@app.get("/api/llm/status")
async def get_llm_status():
    """Get current LLM status"""
    from ..utils.llm_client import llm_client

    return {
        'provider': llm_client.get_provider(),
        'model': llm_client.get_model(),
        'api_key_configured': bool(
            llm_client.api_key and
            not llm_client.api_key.startswith('YOUR_') and
            not llm_client.api_key.startswith('sk-your')
        )
    }
