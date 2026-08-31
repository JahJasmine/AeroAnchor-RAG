/**
 * Aircraft model config — single model
 * ─────────────────────────────────────────────
 * To add a new model:
 *   1. Put the .glb into frontend/public/models/
 *   2. Add a new entry to the MODELS array below
 *   3. In partMap, map GLB node name → display name
 *      (don't know the node name? leave it empty; the page's yellow box will prompt you)
 */

export const MODELS = [
  {
    file: "/models/a380.glb",
    name: "Airbus A380",
    scale: 1.0,
    partMap: {},
    // Organized by the parts a pilot actually needs: categorized by actual geometric position (not just translating the English names).
    // Rules: all real parts are selectable; split meshes of the same type are merged into one part;
    // Parts not of pilot interest are not hidden but merged into adjacent related parts; only hide dummy modeling parts (shadow faces).
    hide: [
      /shadow/,          // Shadow receiver (dummy plane used for rendering, not a real structure)
    ],
    patterns: [
      // —— Engines (4, split by core structure for teaching) ——
      { match: /(^fan|FanBack|FanCasing|FanRoot|fancowl|intake|nosecone)/, label: "Fan & Intake", label_en: "Fan & Intake", desc: "The intake, fan, and spinner cone at the front of the engine, drawing in and initially compressing the airflow.", desc_en: "The intake, fan, and spinner cone at the front of the engine, drawing in and initially compressing the airflow." },
      { match: /(CompH|Stage\dH|TurbineH)/, label: "Compressor & Turbine", label_en: "Compressor & Turbine", desc: "The high-pressure compressor and turbine stages of the engine core, compressing air stage by stage and driving the fan.", desc_en: "The high-pressure compressor and turbine stages of the engine core, compressing air stage by stage and driving the fan." },
      { match: /(bypass|cascade|NozzleH|reverse)/, label: "Bypass Duct & Exhaust", label_en: "Bypass Duct & Exhaust", desc: "Bypass duct, thrust reverser, and exhaust nozzle, controlling the jet flow and thrust direction.", desc_en: "Bypass duct, thrust reverser, and exhaust nozzle, controlling the jet flow and thrust direction." },
      { match: /(cowl|Cylinder01|Object01|poly|rim)/, label: "Engine Nacelle", label_en: "Engine Nacelle", desc: "Nacelle and cowling surrounding the engine core.", desc_en: "Nacelle and cowling surrounding the engine core." },
      { match: /pylon/, label: "Engine Pylon", label_en: "Engine Pylon", desc: "Load-bearing structure that suspends the engine under the wing.", desc_en: "Load-bearing structure that suspends the engine under the wing." },
      // —— Control surfaces ——
      { match: /^aileron\d+$/, label: "Aileron", label_en: "Aileron", desc: "Control surface on the outboard trailing edge of the wing, controlling roll.", desc_en: "Control surface on the outboard trailing edge of the wing, controlling roll." },
      { match: /^flap\d+$/, label: "Flap", label_en: "Flap", desc: "High-lift device on the wing trailing edge, extended for extra lift during takeoff and landing.", desc_en: "High-lift device on the wing trailing edge, extended for extra lift during takeoff and landing." },
      { match: /^spoiler\d+$/, label: "Spoiler", label_en: "Spoiler", desc: "Retractable speed brakes on the upper wing surface, used for deceleration and roll assist.", desc_en: "Retractable speed brakes on the upper wing surface, used for deceleration and roll assist." },
      { match: /^slat|^slot/, label: "Leading-Edge Slat", label_en: "Leading-Edge Slat", desc: "Slats and slots on the wing leading edge, improving low-speed performance at high angles of attack.", desc_en: "Slats and slots on the wing leading edge, improving low-speed performance at high angles of attack." },
      { match: /^elev\d+$/, label: "Elevator", label_en: "Elevator", desc: "Control surface on the horizontal tail trailing edge, controlling pitch.", desc_en: "Control surface on the horizontal tail trailing edge, controlling pitch." },
      { match: /rudder/, label: "Rudder", label_en: "Rudder", desc: "Control surface on the vertical tail trailing edge, controlling yaw.", desc_en: "Control surface on the vertical tail trailing edge, controlling yaw." },
      // —— Wing (structure merged; control surfaces / wingtips / fairings listed separately) ——
      { match: /^FTF[MS]/, label: "Flap Track Fairing", label_en: "Flap Track Fairing", desc: "Streamlined 'canoe' fairings under the wing trailing edge, housing flap tracks and actuators.", desc_en: "Streamlined 'canoe' fairings under the wing trailing edge, housing flap tracks and actuators." },
      { match: /^winglet|^tip[LR]$/, label: "Winglet", label_en: "Winglet", desc: "Upright fins at the wing tips, reducing wingtip vortices and induced drag.", desc_en: "Upright fins at the wing tips, reducing wingtip vortices and induced drag." },
      { match: /^(wingseg|leading|trailing)|^Box01$|static_disc/, label: "Wing", label_en: "Wing", desc: "Wing load-bearing structure: leading edge, trailing edge, center wing box, and static discharge wicks, providing lift and containing fuel.", desc_en: "Wing load-bearing structure: leading edge, trailing edge, center wing box, and static discharge wicks, providing lift and containing fuel." },
      // —— Tail ——
      { match: /stabilizer|^tips$/, label: "Horizontal Stabilizer", label_en: "Horizontal Stabilizer", desc: "Horizontal stabilizer, providing longitudinal stability (including tip structure).", desc_en: "Horizontal stabilizer, providing longitudinal stability (including tip structure)." },
      { match: /vstab/, label: "Vertical Stabilizer", label_en: "Vertical Stabilizer", desc: "Vertical stabilizer, providing directional stability.", desc_en: "Vertical stabilizer, providing directional stability." },
      // —— Landing gear (including doors) ——
      { match: /gear_cover|gearbay|nosegrdoor|^door\d/, label: "Landing Gear & Doors", label_en: "Landing Gear & Doors", desc: "Landing gear and its doors, used for ground taxiing and takeoff/landing cushioning (door1B~4B are main gear doors).", desc_en: "Landing gear and its doors, used for ground taxiing and takeoff/landing cushioning (door1B~4B are main gear doors)." },
      // —— Fuselage ——
      { match: /fuselage|bodyfairing|belly|bathtub|windscreen|extras/, label: "Fuselage", label_en: "Fuselage", desc: "Fuselage skin and fairing structure, housing the passenger cabin, cockpit, and cargo hold.", desc_en: "Fuselage skin and fairing structure, housing the passenger cabin, cockpit, and cargo hold." },
    ],
  },
];

// Default: select the first model
export const DEFAULT_MODEL_INDEX = 0; // Airbus A380
