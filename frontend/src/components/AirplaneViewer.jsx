import { useRef, useMemo, useState, useCallback, useEffect, Suspense } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import React from 'react'
import { pick, t } from '../config/locale'

// ═══════════════════════════════════════════════════════════════════
// Analyze the model, grouped by partMap
// ═══════════════════════════════════════════════════════════════════

// Resolve the part config by exact-name partMap or regex patterns
// Used to merge split-up parts of the same kind like aileron01~06 and elev1~4 into a single part
function resolvePartConfig(key, partMap, patterns) {
  // 1) exact name takes priority
  if (partMap[key]) return partMap[key]
  // 2) regex match (in declaration order, first hit wins)
  for (const p of patterns || []) {
    if (p.match && p.match.test(key)) return p
  }
  return null
}

// Whether a part should be hidden (shadow planes, generic modeling residue, etc.): not shown in the list and not rendered
function isHidden(key, hide) {
  for (const h of hide || []) {
    if (h.test(key)) return true
  }
  return false
}

function analyzeModel(scene, partMap, patterns, hide) {
  scene.updateMatrixWorld()
  const meshList = []
  let counter = 0
  scene.traverse((child) => {
    if (!child.isMesh) return
    let key = (child.name?.trim()) || (child.parent?.name?.trim()) || ''
    if (!key) key = `Unnamed_${++counter}`
    if (isHidden(key, hide)) return
    meshList.push({ mesh: child, key })
  })

  const groups = {}
  for (const { mesh, key } of meshList) {
    const cfg = resolvePartConfig(key, partMap, patterns)
    // placeholders don't count as a valid config
    const isValid = cfg && cfg.label && cfg.label !== 'Enter part name here'
    const label = isValid ? pick(cfg.label, cfg.label_en) : key
    if (!groups[label]) groups[label] = { meshes: [], configured: isValid, desc: isValid ? pick(cfg.desc || '', cfg.desc_en) : '' }
    groups[label].meshes.push(mesh)
  }
  return { groups }
}

// ═══════════════════════════════════════════════════════════════════
// Scene
// ═══════════════════════════════════════════════════════════════════

function SceneContent({ modelPath, partMap, patterns, hide, modelScale, selectedParts, highlightedParts, hoveredPart, onPartHover, onPartClick, onReady }) {
  const gltf = useGLTF(modelPath)

  // clone + manual centering + auto scale (mimicking 3DCellForge)
  const { scene, groups } = useMemo(() => {
    const cloned = gltf.scene.clone(true)

    // preprocess materials + hide shadow and other modeling residue
    cloned.traverse((node) => {
      if (!node.isMesh) return
      const nm = node.name?.trim() || ''
      if (isHidden(nm, hide)) { node.visible = false; return }
      node.castShadow = true
      node.receiveShadow = true
      if (node.material) {
        if (Array.isArray(node.material)) {
          node.material = node.material.map(m => prepMaterial(m))
        } else {
          node.material = prepMaterial(node.material)
        }
      }
    })

    // center
    const box = new THREE.Box3().setFromObject(cloned)
    const center = box.getCenter(new THREE.Vector3())
    cloned.position.sub(center)

    // auto scale
    const size = box.getSize(new THREE.Vector3())
    const longest = Math.max(size.x, size.y, size.z) || 1
    const autoScale = 5 / longest

    const { groups: g } = analyzeModel(cloned, partMap, patterns, hide)
    return { scene: cloned, groups: g }
  }, [gltf.scene, partMap, patterns, hide])

  useEffect(() => {
    const list = Object.entries(groups).map(([label, g]) => ({
      name: label, label, desc: g.desc || '', matched: g.configured, meshCount: g.meshes.length,
    }))
    let mc = 0; scene.traverse(c => { if (c.isMesh) mc++ })
    onReady?.({ parts: list, meshCount: mc })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // mesh → label mapping
  const meshLabelMap = useMemo(() => {
    const map = new Map()
    for (const [label, g] of Object.entries(groups)) {
      for (const mesh of g.meshes) map.set(mesh, label)
    }
    return map
  }, [groups])

  // per frame: highlight (only change emissive, don't clone materials)
  const controlsRef = useRef(null)
  const { camera } = useThree()

  // Debug: print whether AI-highlighted parts reach this component and match the model groups
  useEffect(() => {
    if (!highlightedParts?.length) return
    const groupLabels = Object.keys(groups)
    const matched = highlightedParts.filter(l => groupLabels.includes(l))
    const missing = highlightedParts.filter(l => !groupLabels.includes(l))
    console.log('[viewer] highlightedParts=', JSON.stringify(highlightedParts),
      'matched=', JSON.stringify(matched),
      missing.length ? '⚠️ MISSING(no such group)=' + JSON.stringify(missing) : '')
  }, [highlightedParts, groups])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    for (const [label, g] of Object.entries(groups)) {
      const sel = selectedParts?.includes(label)
      const ai = highlightedParts?.includes(label)
      const hov = hoveredPart === label
      const dim = (selectedParts?.length > 0 || highlightedParts?.length > 0) && !sel && !ai

      for (const mesh of g.meshes) {
        const mat = mesh.material
        if (!mat) continue
        // handle material arrays
        const mats = Array.isArray(mat) ? mat : [mat]
        for (const m of mats) {
          if (!m.emissive) continue
          if (ai) {
            // parts the AI is explaining: red breathing pulse, highest priority (overrides manual yellow to stay visible)
            m.emissive.set(0xff4444)
            m.emissiveIntensity = 0.7 + 0.5 * (0.5 + 0.5 * Math.sin(t * 5))
          } else if (sel) {
            m.emissive.set(0xffd600)
            m.emissiveIntensity = 0.7
          } else if (hov) {
            m.emissive.set(0xaaaaaa)
            m.emissiveIntensity = 0.3
          } else if (dim) {
            m.emissive.set(0x000000)
            m.emissiveIntensity = 0
          } else {
            m.emissive.set(0x000000)
            m.emissiveIntensity = 0
          }
        }
      }
    }
  })

  // raycast
  const { raycaster, pointer, gl } = useThree()
  const allMeshes = useMemo(() => Object.values(groups).flatMap(g => g.meshes), [groups])
  const downPos = useRef({ x: 0, y: 0 })

  const raycast = useCallback(() => {
    raycaster.setFromCamera(pointer, camera)
    const hits = raycaster.intersectObjects(allMeshes, false)
    if (hits.length > 0) return meshLabelMap.get(hits[0].object) || null
    return null
  }, [camera, raycaster, pointer, allMeshes, meshLabelMap])

  useEffect(() => {
    const el = gl.domElement; if (!el) return
    const onDown = (e) => { downPos.current = { x: e.clientX, y: e.clientY } }
    const onUp = (e) => {
      const dx = e.clientX - downPos.current.x, dy = e.clientY - downPos.current.y
      if (Math.sqrt(dx * dx + dy * dy) < 4) { const hit = raycast(); if (hit) onPartClick(hit) }
    }
    const onMove = () => onPartHover(raycast())
    el.addEventListener('pointerdown', onDown); el.addEventListener('pointerup', onUp); el.addEventListener('pointermove', onMove)
    return () => { el.removeEventListener('pointerdown', onDown); el.removeEventListener('pointerup', onUp); el.removeEventListener('pointermove', onMove) }
  }, [gl, raycast, onPartHover, onPartClick])

  const resetView = useCallback(() => {
    if (controlsRef.current) controlsRef.current.reset()
  }, [])

  // expose reset to the outside
  useEffect(() => {
    window.__airplaneReset = resetView
    return () => { delete window.__airplaneReset }
  }, [resetView])

  return (
    <group scale={modelScale}>
      <primitive object={scene} />
      <OrbitControls ref={controlsRef} makeDefault enablePan enableZoom enableRotate enableDamping dampingFactor={0.08} />
    </group>
  )
}

// ═══════════════════════════════════════════════════════════════════
// Material preprocessing (mimicking 3DCellForge GeneratedGlbModel)
// ═══════════════════════════════════════════════════════════════════

function prepMaterial(mat) {
  const cloned = mat.clone?.() ?? new THREE.MeshStandardMaterial({ color: '#dbe7ea', roughness: 0.42, metalness: 0.04 })
  cloned.side = THREE.DoubleSide
  cloned.envMapIntensity = Math.max(cloned.envMapIntensity || 0, 1.2)
  cloned.needsUpdate = true
  return cloned
}

// ═══════════════════════════════════════════════════════════════════
// Shell
// ═══════════════════════════════════════════════════════════════════

export default function AirplaneViewer({ modelPath, partMap, patterns, hide, modelScale, selectedParts, highlightedParts, hoveredPart, onPartHover, onPartClick, onPartsDiscovered }) {
  const [status, setStatus] = useState(null)

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#f5efdf' }}>

      <Canvas
        camera={{ position: [0, 0.1, 6], fov: 35 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl }) => {
          gl.toneMapping = THREE.ACESFilmicToneMapping
          gl.toneMappingExposure = 1.1
        }}
        key={modelPath}
      >
        <color attach="background" args={['#f5efdf']} />
        <ambientLight intensity={0.82} />
        <directionalLight position={[4, 5, 5]} intensity={3.4} color="#fff7ed" />
        <directionalLight position={[-4.5, 2.6, 3]} intensity={1.65} color="#dbeafe" />
        <pointLight position={[0, -3.2, 2.4]} intensity={1.35} color="#f9a8d4" />
        <pointLight position={[-2.4, 1.2, 1.6]} intensity={0.75} color="#b8f7a6" />

        <Suspense fallback={null}>
          <SceneContent
            modelPath={modelPath}
            partMap={partMap}
            patterns={patterns}
            hide={hide}
            modelScale={modelScale}
            selectedParts={selectedParts}
            highlightedParts={highlightedParts}
            hoveredPart={hoveredPart}
            onPartHover={onPartHover}
            onPartClick={onPartClick}
            onReady={({ parts, meshCount }) => {
              setStatus({ parts, meshCount })
              onPartsDiscovered?.(parts)
            }}
          />
        </Suspense>
      </Canvas>

      <button onClick={() => window.__airplaneReset?.()} style={{
        position: 'absolute', bottom: 20, left: 210, zIndex: 20,
        padding: '8px 16px', borderRadius: 10, border: '1px solid #888',
        background: 'rgba(0,0,0,0.6)', color: '#ccc', fontSize: 13,
        cursor: 'pointer', fontFamily: 'inherit', backdropFilter: 'blur(8px)',
      }}>
        {t('resetView')}
      </button>
    </div>
  )
}
