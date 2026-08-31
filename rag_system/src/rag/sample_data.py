SAMPLE_DOCUMENTS = {
    'rag_aircraft_params': [
        {'id': 'param_1', 'text': 'Aircraft: Cessna 172, max takeoff weight: 2550 lbs, stall speed: 48 knots (flaps down)', 'metadata': {'type': 'Aircraft Parameters'}},
        {'id': 'param_2', 'text': 'V speeds: Vx (best angle of climb speed) - 62 knots, Vy (best rate of climb speed) - 74 knots', 'metadata': {'type': 'V Speeds'}},
        {'id': 'param_3', 'text': 'Flight limits: maximum operating speed Vmo - 160 knots, flap operating speed Vfe - 110 knots', 'metadata': {'type': 'Flight Limits'}},
        {'id': 'param_4', 'text': 'Safety red lines: stall warning, overspeed warning, low altitude warning, abnormal engine parameters', 'metadata': {'type': 'Safety Red Lines'}},
    ],
    'rag_checklists': [
        {'id': 'check_1', 'text': 'Normal checklist - before takeoff: 1. Altimeter setting 2. Navigation equipment 3. Flap setting 4. Trim check', 'metadata': {'type': 'Normal Checklist'}},
        {'id': 'check_2', 'text': 'Emergency procedure - engine failure: 1. Maintain speed 2. Select forced landing site 3. Shut off fuel 4. Flap setting', 'metadata': {'type': 'Emergency Procedure'}},
    ],
    'rag_manipulation': [
        {'id': 'manip_1', 'text': 'Control mapping: control stick - controls elevator and ailerons, rudder pedals - control rudder', 'metadata': {'type': 'Control Mapping'}},
        {'id': 'manip_2', 'text': 'Atomic actions: push stick - lower nose/increase airspeed, pull stick - raise nose/decrease airspeed', 'metadata': {'type': 'Atomic Actions'}},
    ],
    'rag_performance': [
        {'id': 'perf_1', 'text': 'Performance data: climb rate 700 ft/min, stall speed 48 knots, max endurance 4.5 hours', 'metadata': {'type': 'Performance'}},
        {'id': 'perf_2', 'text': 'Envelope data: normal flight envelope - speed range 48-160 knots, load factor limit +4/-2G', 'metadata': {'type': 'Envelope Data'}},
    ],
    'rag_emergency': [
        {'id': 'emerg_1', 'text': 'Emergency procedure - stall recovery: 1. Push stick to reduce angle of attack 2. Full throttle 3. Level the wings', 'metadata': {'type': 'Emergency Procedure'}},
    ],
    'rag_general': [
        {'id': 'gen_1', 'text': 'Weather scenario: visual flight rules, visibility >5 miles, cloud base >1000 ft', 'metadata': {'type': 'Weather Scenario'}},
        {'id': 'gen_2', 'text': 'License requirements: private pilot requirements - 40 hours flight time, pass written and oral exams', 'metadata': {'type': 'License Requirements'}},
    ],
    'rag_acs': [
        {'id': 'acs_1', 'text': 'Subject dimensions: takeoff, climb, cruise, descent, approach, landing', 'metadata': {'type': 'Subject Dimensions'}},
        {'id': 'acs_2', 'text': 'Rating levels: excellent - fully meets standards, good - basically meets, pass - barely passes', 'metadata': {'type': 'Rating Levels'}},
    ],
    'rag_components': [
        {'id': 'comp_1', 'text': 'Component: elevator - controls aircraft pitch, located on the trailing edge of the horizontal stabilizer', 'metadata': {'type': 'Component'}},
        {'id': 'comp_2', 'text': 'Component: aileron - controls aircraft roll, located on the outer trailing edge of the wing', 'metadata': {'type': 'Component'}},
    ],
    'rag_regulations': [
        {'id': 'reg_1', 'text': 'Regulation clause: FAR Part 91 - general operating rules, including airspeed limits and altitude rules', 'metadata': {'type': 'Regulation Clause'}},
    ]
}

def populate_sample_data(rag_instances: Dict[str, RAGInstance]):
    """Populate sample data into RAG instances"""
    for rag_name, documents in SAMPLE_DOCUMENTS.items():
        if rag_name in rag_instances:
            rag_instances[rag_name].add_documents(documents)
            print(f"Populated {rag_name} complete, added {len(documents)} documents")
