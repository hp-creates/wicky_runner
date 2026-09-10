import React, { useRef, useEffect, useState, useCallback } from 'react'
import { ExternalLink, Maximize2, Minimize2, ZoomIn, ZoomOut, RotateCcw, X, Sparkles } from 'lucide-react'

/**
 * Litmaps-style Floating Node Constellation Graph.
 * Renders glowing white nodes, geometric connecting lines, traveling pulses,
 * zero-gravity floating micro-motion, drag-and-drop, zoom/pan, and node inspection.
 */
export default function FloatingGraph({
  nodes = [],
  edges = [],
  selectedStep = null,
  onSelectNode = () => { },
  traversing = false,
  statusMessage = '',
  isFullscreen = false,
  onToggleFullscreen = () => { }
}) {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)

  // Viewport transformation: pan and zoom
  const [viewState, setViewState] = useState({
    panX: 0,
    panY: 0,
    zoom: 1.0
  })

  // Selected node for glassmorphic inspector
  const [activeNode, setActiveNode] = useState(null)
  const [hoveredNode, setHoveredNode] = useState(null)

  // Local mutable copy of node positions so dragging & physics are fluid without React rerender lag
  const graphStateRef = useRef({
    nodes: [],
    edges: [],
    draggedNodeId: null,
    isPanning: false,
    panStart: { x: 0, y: 0 },
    dragOffset: { x: 0, y: 0 },
    hasMoved: false,
    dimensions: { width: 800, height: 600 }
  })

  // Sync incoming props to internal ref
  useEffect(() => {
    if (!nodes || nodes.length === 0) {
      graphStateRef.current.nodes = []
      graphStateRef.current.edges = []
      return
    }

    // Preserve existing node positions if id matches, otherwise assign layout position
    const currentNodesMap = new Map(graphStateRef.current.nodes.map(n => [n.id, n]))

    const mappedNodes = nodes.map((n, idx) => {
      const existing = currentNodesMap.get(n.id)
      const phase = (idx * 1.37) % (Math.PI * 2)
      return {
        ...n,
        // Base coordinate in world space
        baseX: existing ? existing.baseX : (n.x ?? (idx * 140 - (nodes.length * 70))),
        baseY: existing ? existing.baseY : (n.y ?? (Math.sin(idx * 0.8) * 60)),
        currentX: existing ? existing.currentX : (n.x ?? 0),
        currentY: existing ? existing.currentY : (n.y ?? 0),
        phaseX: phase,
        phaseY: phase + Math.PI / 2,
        radius: n.is_target ? 9 : (n.is_start ? 8 : (n.is_path ? 7 : 4.5)),
        floatSpeed: 0.0012 + (idx % 3) * 0.0003
      }
    })

    graphStateRef.current.nodes = mappedNodes
    graphStateRef.current.edges = edges || []

    // Center and frame constellation
    fitConstellation(mappedNodes)
  }, [nodes, edges])

  // Center constellation in the viewport
  const fitConstellation = useCallback((targetNodes = graphStateRef.current.nodes) => {
    if (!targetNodes || targetNodes.length === 0) return
    const container = containerRef.current
    if (!container) return

    const { clientWidth: w, clientHeight: h } = container
    if (w === 0 || h === 0) return

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
    targetNodes.forEach(n => {
      minX = Math.min(minX, n.baseX)
      maxX = Math.max(maxX, n.baseX)
      minY = Math.min(minY, n.baseY)
      maxY = Math.max(maxY, n.baseY)
    })

    const boundsW = Math.max(120, maxX - minX + 280)
    const boundsH = Math.max(120, maxY - minY + 260)
    const scaleX = (w - 60) / boundsW
    const scaleY = (h - 160) / boundsH
    const newZoom = Math.max(0.65, Math.min(1.3, Math.min(scaleX, scaleY)))

    const centerX = (minX + maxX) / 2
    const centerY = (minY + maxY) / 2

    // Shift center upwards by 40px so constellation sits comfortably above bottom route HUD
    setViewState({
      zoom: newZoom,
      panX: w / 2 - centerX * newZoom,
      panY: (h / 2 - 40) - centerY * newZoom
    })
  }, [])

  // Resize handler
  useEffect(() => {
    const handleResize = () => {
      const container = containerRef.current
      const canvas = canvasRef.current
      if (!container || !canvas) return

      const dpr = window.devicePixelRatio || 1
      const w = container.clientWidth
      const h = container.clientHeight

      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`

      graphStateRef.current.dimensions = { width: w, height: h }
    }

    handleResize()
    const ro = new ResizeObserver(handleResize)
    if (containerRef.current) ro.observe(containerRef.current)

    return () => ro.disconnect()
  }, [])

  // Animation Loop (60 FPS Litmaps Canvas Renderer)
  useEffect(() => {
    let animationFrameId
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')

    // Background star dust / celestial points for depth
    const stars = Array.from({ length: 48 }, (_, i) => ({
      x: (Math.sin(i * 99.1) * 0.5 + 0.5) * 1600 - 800,
      y: (Math.cos(i * 47.7) * 0.5 + 0.5) * 1200 - 600,
      size: (i % 3 === 0 ? 1.5 : 1),
      alpha: 0.15 + (i % 5) * 0.08
    }))

    const render = (time) => {
      const dpr = window.devicePixelRatio || 1
      const { width: w, height: h } = graphStateRef.current.dimensions
      if (w === 0 || h === 0) {
        animationFrameId = requestAnimationFrame(render)
        return
      }

      ctx.save()
      ctx.scale(dpr, dpr)

      // 1. Clear background: deep obsidian/slate canvas (#0c0f14)
      ctx.fillStyle = '#0c0f14'
      ctx.fillRect(0, 0, w, h)

      // Subtle radial ambient vignette
      const bgGrad = ctx.createRadialGradient(w / 2, h / 2, 40, w / 2, h / 2, Math.max(w, h) * 0.75)
      bgGrad.addColorStop(0, 'rgba(26, 32, 44, 0.45)')
      bgGrad.addColorStop(0.6, 'rgba(12, 15, 20, 0.85)')
      bgGrad.addColorStop(1, '#090b0e')
      ctx.fillStyle = bgGrad
      ctx.fillRect(0, 0, w, h)

      // Apply Viewport Transformation (Pan & Zoom)
      ctx.save()
      ctx.translate(viewState.panX, viewState.panY)
      ctx.scale(viewState.zoom, viewState.zoom)

      // 2. Draw faint celestial stars in background
      stars.forEach(s => {
        ctx.fillStyle = `rgba(255, 255, 255, ${s.alpha})`
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.size / viewState.zoom, 0, Math.PI * 2)
        ctx.fill()
      })

      // 3. Update floating coordinates for each node
      const currentNodes = graphStateRef.current.nodes
      const nodeMap = new Map()

      currentNodes.forEach(n => {
        // If node is being dragged by user, hold its base position directly
        if (graphStateRef.current.draggedNodeId === n.id) {
          n.currentX = n.baseX
          n.currentY = n.baseY
        } else {
          // Organic zero-gravity floating oscillation (Litmap celestial float)
          const floatX = Math.sin(time * n.floatSpeed + n.phaseX) * 5
          const floatY = Math.cos(time * (n.floatSpeed * 1.15) + n.phaseY) * 7
          n.currentX = n.baseX + floatX
          n.currentY = n.baseY + floatY
        }
        nodeMap.set(n.id, n)
      })

      // 4. Draw Connecting Edges (Thin geometric lines as in reference image)
      const currentEdges = graphStateRef.current.edges

      // (A) Draw Candidate / Constellation edges first (thin, faint)
      currentEdges.forEach(edge => {
        if (edge.is_path) return
        const src = nodeMap.get(edge.source)
        const tgt = nodeMap.get(edge.target)
        if (!src || !tgt) return

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.16)'
        ctx.lineWidth = 1.0 / viewState.zoom
        ctx.setLineDash([3, 4])
        ctx.beginPath()
        ctx.moveTo(src.currentX, src.currentY)
        ctx.lineTo(tgt.currentX, tgt.currentY)
        ctx.stroke()
        ctx.setLineDash([])
      })

      // (B) Draw Active Path Edges (Crisp glowing lines, strictly acyclic start -> hops -> target)
      currentEdges.forEach((edge, eIdx) => {
        if (!edge.is_path) return
        const src = nodeMap.get(edge.source)
        const tgt = nodeMap.get(edge.target)
        if (!src || !tgt) return

        // Outer glow
        ctx.shadowColor = 'rgba(255, 255, 255, 0.6)'
        ctx.shadowBlur = 8
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.75)'
        ctx.lineWidth = 2.0 / viewState.zoom
        ctx.beginPath()
        ctx.moveTo(src.currentX, src.currentY)
        ctx.lineTo(tgt.currentX, tgt.currentY)
        ctx.stroke()

        // Reset shadow
        ctx.shadowBlur = 0

        // Traveling energy pulse / photon along the active path (shows acyclic direction of traversal!)
        const dx = tgt.currentX - src.currentX
        const dy = tgt.currentY - src.currentY
        const dist = Math.hypot(dx, dy)
        if (dist > 1) {
          const speed = 0.0006
          const offset = (eIdx * 0.3)
          const progress = ((time * speed + offset) % 1.0)
          const px = src.currentX + dx * progress
          const py = src.currentY + dy * progress

          // Draw traveling photon
          ctx.fillStyle = '#ffffff'
          ctx.shadowColor = 'rgba(255, 255, 255, 0.95)'
          ctx.shadowBlur = 10
          ctx.beginPath()
          ctx.arc(px, py, 3.2 / viewState.zoom, 0, Math.PI * 2)
          ctx.fill()
          ctx.shadowBlur = 0
        }
      })

      // 5. Draw Nodes (White glowing dots matching user image)
      currentNodes.forEach((n, idx) => {
        const isHovered = hoveredNode?.id === n.id
        const isSelected = activeNode?.id === n.id || selectedStep === n.hop_index

        // (A) Faint leader line to label (just like in the reference image)
        const labelText = n.is_path
          ? (n.label || `NODE_${String(idx + 1).padStart(2, '0')}`)
          : (n.title.toUpperCase())

        const labelOffsetDist = 18 + (n.radius * 1.2)
        // Position label above or angled based on node index
        const angle = n.is_path ? -Math.PI / 3 : (idx % 2 === 0 ? Math.PI / 4 : -Math.PI / 4)
        const lx = n.currentX + Math.cos(angle) * labelOffsetDist
        const ly = n.currentY + Math.sin(angle) * labelOffsetDist

        // (B) Outer Radiant Glow
        ctx.shadowColor = isSelected
          ? '#f59e0b'
          : (n.is_start ? '#10b981' : (n.is_target ? '#f59e0b' : 'rgba(255, 255, 255, 0.9)'))
        ctx.shadowBlur = isHovered || isSelected ? 20 : (n.is_path ? 12 : 6)

        // Outer Ring for Selected / Start / Target
        if (n.is_start || n.is_target || isSelected) {
          ctx.strokeStyle = n.is_start ? '#10b981' : '#f59e0b'
          ctx.lineWidth = 1.8 / viewState.zoom
          ctx.beginPath()
          const pulseR = n.radius + (isSelected ? 5 + Math.sin(time * 0.005) * 2 : 3)
          ctx.arc(n.currentX, n.currentY, pulseR, 0, Math.PI * 2)
          ctx.stroke()
        }

        // Inner Solid White Core (Matches user reference image)
        ctx.fillStyle = '#ffffff'
        ctx.beginPath()
        ctx.arc(n.currentX, n.currentY, n.radius + (isHovered ? 2 : 0), 0, Math.PI * 2)
        ctx.fill()

        ctx.shadowBlur = 0

        // (C) Render Clean Technical Monospace Label
        ctx.font = `${n.is_path ? 'bold 10px' : '9px'} 'JetBrains Mono', 'SF Mono', 'Courier New', monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'

        // Text background pill for crisp legibility
        const metrics = ctx.measureText(labelText)
        const padX = 6
        const padY = 3
        const tw = metrics.width + padX * 2
        const th = 14

        // Draw small connector line from node to label box
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)'
        ctx.lineWidth = 0.8 / viewState.zoom
        ctx.beginPath()
        ctx.moveTo(n.currentX, n.currentY)
        ctx.lineTo(lx, ly)
        ctx.stroke()

        // Background pill
        ctx.fillStyle = isSelected
          ? 'rgba(245, 158, 11, 0.25)'
          : (n.is_path ? 'rgba(15, 18, 24, 0.85)' : 'rgba(12, 15, 20, 0.75)')
        ctx.strokeStyle = isSelected
          ? '#f59e0b'
          : (n.is_path ? 'rgba(255, 255, 255, 0.4)' : 'rgba(255, 255, 255, 0.15)')
        ctx.lineWidth = 1.0 / viewState.zoom

        ctx.beginPath()
        ctx.roundRect(lx - tw / 2, ly - th / 2, tw, th, 3)
        ctx.fill()
        ctx.stroke()

        // Text string
        ctx.fillStyle = isSelected
          ? '#f59e0b'
          : (n.is_path ? '#f0f6fc' : 'rgba(240, 246, 252, 0.65)')
        ctx.fillText(labelText, lx, ly)
      })

      ctx.restore() // Restore world transform
      ctx.restore() // Restore DPR scale

      animationFrameId = requestAnimationFrame(render)
    }

    animationFrameId = requestAnimationFrame(render)
    return () => cancelAnimationFrame(animationFrameId)
  }, [viewState, hoveredNode, activeNode, selectedStep])

  // Mouse & Gesture Handlers (Smooth Drag, Pan, Zoom)
  const getCanvasCoords = (e) => {
    const canvas = canvasRef.current
    if (!canvas) return { x: 0, y: 0 }
    const rect = canvas.getBoundingClientRect()
    const clientX = e.clientX ?? e.touches?.[0]?.clientX ?? 0
    const clientY = e.clientY ?? e.touches?.[0]?.clientY ?? 0
    const screenX = clientX - rect.left
    const screenY = clientY - rect.top
    // Convert screen coordinates to world coordinates
    const worldX = (screenX - viewState.panX) / viewState.zoom
    const worldY = (screenY - viewState.panY) / viewState.zoom
    return { screenX, screenY, worldX, worldY }
  }

  const findHitNode = (worldX, worldY) => {
    const hitPadding = 20 / viewState.zoom
    const nodes = graphStateRef.current.nodes
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i]
      const dist = Math.hypot(n.currentX - worldX, n.currentY - worldY)
      if (dist <= n.radius + hitPadding) {
        return n
      }
    }
    return null
  }

  const handleMouseDown = (e) => {
    const { screenX, screenY, worldX, worldY } = getCanvasCoords(e)
    const hit = findHitNode(worldX, worldY)

    graphStateRef.current.hasMoved = false

    if (hit) {
      // Begin dragging node
      graphStateRef.current.draggedNodeId = hit.id
      graphStateRef.current.dragOffset = {
        x: hit.baseX - worldX,
        y: hit.baseY - worldY
      }
    } else {
      // Begin panning canvas
      graphStateRef.current.isPanning = true
      graphStateRef.current.panStart = {
        x: screenX - viewState.panX,
        y: screenY - viewState.panY
      }
    }
  }

  const handleMouseMove = (e) => {
    const { screenX, screenY, worldX, worldY } = getCanvasCoords(e)
    const state = graphStateRef.current

    if (state.draggedNodeId) {
      state.hasMoved = true
      const targetNode = state.nodes.find(n => n.id === state.draggedNodeId)
      if (targetNode) {
        targetNode.baseX = worldX + state.dragOffset.x
        targetNode.baseY = worldY + state.dragOffset.y
      }
    } else if (state.isPanning) {
      state.hasMoved = true
      setViewState(prev => ({
        ...prev,
        panX: screenX - state.panStart.x,
        panY: screenY - state.panStart.y
      }))
    } else {
      // Hover detection
      const hit = findHitNode(worldX, worldY)
      if (hit !== hoveredNode) {
        setHoveredNode(hit)
      }
    }
  }

  const handleMouseUp = (e) => {
    const state = graphStateRef.current
    if (!state.hasMoved) {
      // It was a crisp click!
      const { worldX, worldY } = getCanvasCoords(e)
      const hit = findHitNode(worldX, worldY)
      if (hit) {
        setActiveNode(hit)
        if (hit.hop_index !== undefined) {
          onSelectNode(hit.hop_index)
        }
      } else {
        setActiveNode(null)
      }
    }

    state.draggedNodeId = null
    state.isPanning = false
  }

  const handleWheel = (e) => {
    e.preventDefault()
    const { screenX, screenY } = getCanvasCoords(e)
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87
    const newZoom = Math.max(0.4, Math.min(3.0, viewState.zoom * zoomFactor))

    // Zoom centered around cursor position
    const newPanX = screenX - (screenX - viewState.panX) * (newZoom / viewState.zoom)
    const newPanY = screenY - (screenY - viewState.panY) * (newZoom / viewState.zoom)

    setViewState({
      zoom: newZoom,
      panX: newPanX,
      panY: newPanY
    })
  }

  // Zoom controls
  const handleZoomIn = () => {
    setViewState(prev => ({ ...prev, zoom: Math.min(3.0, prev.zoom * 1.25) }))
  }

  const handleZoomOut = () => {
    setViewState(prev => ({ ...prev, zoom: Math.max(0.4, prev.zoom * 0.8) }))
  }

  return (
    <div
      ref={containerRef}
      className="floating-graph-container"
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        backgroundColor: '#0c0f14',
        overflow: 'hidden',
        userSelect: 'none',
        cursor: hoveredNode ? 'pointer' : (graphStateRef.current.isPanning ? 'grabbing' : 'grab')
      }}
    >
      {/* HTML5 Render Canvas */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        style={{ display: 'block', width: '100%', height: '100%' }}
      />

      {/* Graph Header Badge & Fullscreen Toggle */}
      <div className="graph-panel-header">
        <span style={{ color: '#f59e0b', fontWeight: 'bold' }}>◈</span>
        <span>Click each node, to see more about them.</span>
      </div>

      <button
        onClick={onToggleFullscreen}
        className="graph-toggle-fullscreen-btn"
        title={isFullscreen ? 'Exit Fullscreen' : 'View Fullscreen Graph'}
      >
        {isFullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
        <span>{isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}</span>
      </button>

      {/* Floating Canvas Controls (Bottom Right) */}
      <div className="graph-floating-controls">
        <button onClick={() => fitConstellation()} className="graph-ctrl-btn" title="Fit & Recenter Constellation">
          <RotateCcw size={14} />
          <span>Fit Graph</span>
        </button>
        <button onClick={handleZoomIn} className="graph-ctrl-btn-icon" title="Zoom In">
          <ZoomIn size={15} />
        </button>
        <button onClick={handleZoomOut} className="graph-ctrl-btn-icon" title="Zoom Out">
          <ZoomOut size={15} />
        </button>
      </div>

      {/* Live Traversal Status Banner */}
      {traversing && (
        <div className="constellation-radar-overlay">
          <div className="sonar-emitter"></div>
          <Sparkles size={16} color="#f59e0b" className="animate-spin" />
          <span className="radar-status-text">
            {statusMessage || 'Discovering acyclic shortest path...'}
          </span>
        </div>
      )}

      {/* Node Inspection Popover Card */}
      {activeNode && (
        <div className="node-inspector-card">
          <div className="inspector-header">
            <div className="inspector-badge-row">
              <span className={`node-type-pill ${activeNode.type}`}>
                {activeNode.is_start ? 'START NODE' : (activeNode.is_target ? 'TARGET // DESTINATION' : (activeNode.is_path ? `HOP 0${activeNode.hop_index}` : 'CANDIDATE BRANCH'))}
              </span>
              {activeNode.score !== undefined && (
                <span className="node-score-pill">Score: {activeNode.score}</span>
              )}
            </div>
            <button onClick={() => setActiveNode(null)} className="inspector-close-btn">
              <X size={15} />
            </button>
          </div>

          <h4 className="inspector-node-title">{activeNode.title}</h4>
          <p className="inspector-node-desc">
            {activeNode.is_path
              ? `Confirmed step on the shortest route. Connected with verified hyperlink.`
              : `Evaluated branch candidate during heuristic expansion.`}
          </p>

          <div className="inspector-action-row">
            <a
              href={`https://en.wikipedia.org/wiki/${encodeURIComponent(activeNode.title.replace(/ /g, '_'))}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inspector-wiki-link"
            >
              <span>Read on Wikipedia</span>
              <ExternalLink size={13} />
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
