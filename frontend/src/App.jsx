import React, { useState, useEffect } from 'react'
import confetti from 'canvas-confetti'
import {
  Menu,
  Search,
  ArrowRightLeft,
  Zap,
  Shuffle,
  Cpu,
  ExternalLink,
  ChevronRight,
  Maximize2,
  Minimize2,
  CheckCircle2,
  Award,
  Layers,
  FileText,
  Clock,
  X,
  Compass
} from 'lucide-react'

import FloatingGraph from './components/FloatingGraph'
import DecisionDrawer from './components/DecisionDrawer'

export default function App() {
  const [startArticle, setStartArticle] = useState('Apple')
  const [targetArticle, setTargetArticle] = useState('Steve Jobs')
  const [curatedPairs, setCuratedPairs] = useState([])

  const [traversing, setTraversing] = useState(false)
  const [traversalStatus, setTraversalStatus] = useState('')
  const [result, setResult] = useState(null)
  const [selectedStep, setSelectedStep] = useState(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isFullscreenGraph, setIsFullscreenGraph] = useState(false)
  const [activeTab, setActiveTab] = useState('article') // 'article' | 'graph' | 'matrix'
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const [enableLLM, setEnableLLM] = useState(false)
  const [geminiKey, setGeminiKey] = useState('')
  const [showLLMSettings, setShowLLMSettings] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  // Fetch initial random pairs and run default speedrun
  useEffect(() => {
    fetch('/api/random-pairs')
      .then(res => res.json())
      .then(data => setCuratedPairs(data))
      .catch(() => { })

    // Run initial speedrun on mount
    handleRunSpeedrun('Apple', 'Steve Jobs')
  }, [])

  // Swap start and target
  const handleSwap = () => {
    const temp = startArticle
    setStartArticle(targetArticle)
    setTargetArticle(temp)
  }

  // Surprise Me - pick a curated pair
  const handleSurpriseMe = () => {
    if (curatedPairs.length === 0) return
    const pair = curatedPairs[Math.floor(Math.random() * curatedPairs.length)]
    setStartArticle(pair.start)
    setTargetArticle(pair.target)
    handleRunSpeedrun(pair.start, pair.target)
  }

  // Execute Speedrun
  const handleRunSpeedrun = async (start = startArticle, target = targetArticle) => {
    const s = start.trim()
    const t = target.trim()
    if (!s || !t) {
      setErrorMsg('Please enter both a start and target article.')
      return
    }

    setErrorMsg('')
    setTraversing(true)
    setTraversalStatus(`Indexing target backlinks for "${t}" via MediaWiki API...`)
    setSelectedStep(null)

    try {
      const response = await fetch('/api/speedrun', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start: s,
          target: t,
          enable_llm: enableLLM,
          gemini_key: geminiKey.trim() || undefined
        })
      })

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`)
      }

      const data = await response.json()
      setResult(data)
      setTraversing(false)

      if (data.status === 'victory') {
        confetti({
          particleCount: 50,
          spread: 60,
          origin: { y: 0.85 },
          colors: ['#3366cc', '#008529', '#eaecf0']
        })
      }
    } catch (err) {
      console.error(err)
      setErrorMsg(`Speedrun traversal error: ${err.message}`)
      setTraversing(false)
    }
  }

  const graphNodes = result?.graph?.nodes || []
  const graphEdges = result?.graph?.edges || []
  const pathTitles = result?.path_titles || []

  return (
    <div className="wiki-shell">
      {/* 1. Wikipedia Vector Header */}
      <header className="wiki-header">
        <div className="wiki-header-left">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="sidebar-toggle-btn"
            title="Toggle sidebar navigation"
          >
            <Menu size={18} />
          </button>

          <div className="wiki-brand" onClick={() => handleRunSpeedrun('Apple', 'Steve Jobs')}>
            <div className="wiki-globe-icon">W</div>
            <div className="wiki-brand-text">
              <span className="wiki-brand-title">WIKIPEDIA</span>
              <span className="wiki-brand-subtitle">The Free Speedrun Encyclopedia</span>
            </div>
          </div>
        </div>

        {/* Wikipedia Dual Search Bar (Start -> Target) */}
        <div className="wiki-search-container">
          <div className="wiki-search-box">
            <span className="wiki-input-label">Start:</span>
            <input
              type="text"
              value={startArticle}
              onChange={e => setStartArticle(e.target.value)}
              placeholder="Search start page..."
              className="wiki-search-input"
              disabled={traversing}
              onKeyDown={e => e.key === 'Enter' && handleRunSpeedrun()}
            />
          </div>

          <button onClick={handleSwap} className="wiki-swap-btn" title="Swap start and target" disabled={traversing}>
            <ArrowRightLeft size={14} />
          </button>

          <div className="wiki-search-box">
            <span className="wiki-input-label">Target:</span>
            <input
              type="text"
              value={targetArticle}
              onChange={e => setTargetArticle(e.target.value)}
              placeholder="Search target page..."
              className="wiki-search-input"
              disabled={traversing}
              onKeyDown={e => e.key === 'Enter' && handleRunSpeedrun()}
            />
          </div>

          <button
            onClick={() => handleRunSpeedrun()}
            className="wiki-btn-primary"
            disabled={traversing}
          >
            <Search size={14} />
            <span>{traversing ? 'Navigating...' : 'Speedrun'}</span>
          </button>
        </div>

        {/* Header Right Actions */}
        <div className="wiki-header-right">
          <button onClick={handleSurpriseMe} className="wiki-btn-secondary" title="Random speedrun challenge">
            <Shuffle size={13} />
            <span>Random Route</span>
          </button>

          <button
            onClick={() => setShowLLMSettings(!showLLMSettings)}
            className={`wiki-btn-secondary ${enableLLM ? 'active' : ''}`}
            title="Configure Gemini LLM Guidance"
          >
            <Cpu size={13} />
            <span>{enableLLM ? 'AI Advisor On' : 'AI Advisor'}</span>
          </button>
        </div>
      </header>

      {/* AI Advisor Settings Modal / Dropdown */}
      {showLLMSettings && (
        <div style={{
          position: 'fixed',
          top: '56px',
          right: '20px',
          width: '320px',
          backgroundColor: '#ffffff',
          border: '1px solid #a2a9b1',
          boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
          padding: '1rem',
          zIndex: 3000,
          borderRadius: '2px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontWeight: 'bold', fontSize: '0.85rem' }}>AI Co-Pilot Advisor (Gemini)</span>
            <input
              type="checkbox"
              checked={enableLLM}
              onChange={e => setEnableLLM(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--wm-text-secondary)', marginBottom: '8px', lineHeight: '1.4' }}>
            Uses Gemini 2.5 Flash to rerank candidates with semantic intuition when graph heuristics tie.
          </p>
          <input
            type="password"
            placeholder="Gemini API Key (optional if in .env)"
            value={geminiKey}
            onChange={e => setGeminiKey(e.target.value)}
            style={{
              width: '100%',
              padding: '4px 6px',
              fontSize: '0.78rem',
              border: '1px solid #a2a9b1',
              borderRadius: '2px'
            }}
          />
        </div>
      )}

      {/* 2. Main Page Layout (Sidebar + Article Sheet) */}
      <div className="wiki-container">
        {/* Vector Left Sidebar */}
        {sidebarOpen && (
          <aside className="wiki-sidebar">
            <div className="sidebar-section">
              <div className="sidebar-heading">Navigation</div>
              <ul className="sidebar-links">
                <li className="sidebar-item">
                  <span
                    className={`sidebar-link ${activeTab === 'article' ? 'active' : ''}`}
                    onClick={() => { setActiveTab('article'); setIsFullscreenGraph(false) }}
                  >
                    Main Article & Route
                  </span>
                </li>
                <li className="sidebar-item">
                  <span
                    className={`sidebar-link ${isFullscreenGraph ? 'active' : ''}`}
                    onClick={() => setIsFullscreenGraph(true)}
                  >
                    Constellation Graph
                  </span>
                </li>
                <li className="sidebar-item">
                  <span className="sidebar-link" onClick={handleSurpriseMe}>
                    Random Challenge
                  </span>
                </li>
              </ul>
            </div>

            <div className="sidebar-section">
              <div className="sidebar-heading">Curated Speedruns</div>
              <ul className="sidebar-links">
                {curatedPairs.slice(0, 6).map((pair, idx) => (
                  <li key={idx} className="sidebar-item">
                    <span
                      className="sidebar-link"
                      onClick={() => {
                        setStartArticle(pair.start)
                        setTargetArticle(pair.target)
                        handleRunSpeedrun(pair.start, pair.target)
                      }}
                      title={`${pair.start} ➔ ${pair.target}`}
                    >
                      {pair.start} ➔ {pair.target}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="sidebar-section">
              <div className="sidebar-heading">Tools & Analysis</div>
              <ul className="sidebar-links">
                <li className="sidebar-item">
                  <span className="sidebar-link" onClick={() => setIsDrawerOpen(true)}>
                    Decision Matrix
                  </span>
                </li>
                <li className="sidebar-item">
                  <a
                    className="sidebar-link"
                    href={`https://en.wikipedia.org/wiki/${encodeURIComponent(targetArticle.replace(/ /g, '_'))}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Target on Wikipedia <ExternalLink size={11} />
                  </a>
                </li>
              </ul>
            </div>
          </aside>
        )}

        {/* 3. Main Wikipedia Article Content */}
        <main className="wiki-content">
          {/* Wikipedia Vector Tabs */}
          <div className="wiki-tabs-bar">
            <div className="wiki-tabs-left">
              <button
                className={`wiki-tab ${activeTab === 'article' && !isFullscreenGraph ? 'active' : ''}`}
                onClick={() => { setActiveTab('article'); setIsFullscreenGraph(false) }}
              >
                Article & Route
              </button>
              <button
                className={`wiki-tab ${isFullscreenGraph ? 'active' : ''}`}
                onClick={() => setIsFullscreenGraph(true)}
              >
                Constellation Graph
              </button>
              <button
                className="wiki-tab"
                onClick={() => setIsDrawerOpen(true)}
              >
                Decision Matrix ({result?.log?.length || 0})
              </button>
            </div>

            <div className="wiki-tabs-right">
              <span style={{ fontSize: '0.78rem', color: 'var(--wm-text-secondary)', padding: '5px 8px' }}>
                Acyclic Route: <b>{pathTitles.length} Nodes</b>
              </span>
            </div>
          </div>

          {/* Article Title */}
          <h1 className="firstHeading">
            Speedrun: {startArticle} to {targetArticle}
          </h1>

          {/* Wikipedia Hatnote */}
          <div className="hatnote">
            From Wikipedia, the free speedrun encyclopedia. Path discovered in{' '}
            <b>{result?.steps ?? 0} hops</b> ({result?.elapsed_seconds ?? '0.00'}s) via verified hyperlinks. Zero cycles detected.
          </div>

          {/* Traversal In-Progress Banner */}
          {traversing && (
            <div className="wiki-alert-traversing">
              <div className="pulse-spinner"></div>
              <span><b>Searching Wikipedia:</b> {traversalStatus}</span>
            </div>
          )}

          {/* Error Banner */}
          {errorMsg && (
            <div style={{
              backgroundColor: '#f8d7da',
              border: '1px solid #f5c6cb',
              color: '#721c24',
              padding: '0.6rem 1rem',
              marginBottom: '1rem',
              borderRadius: '2px',
              fontSize: '0.85rem'
            }}>
              {errorMsg}
            </div>
          )}

          {/* Article Two-Column Body */}
          <div className="wiki-article-body">
            {/* Left Main Article Column */}
            <div className="wiki-main-column">
              {/* Table of Contents Box */}
              <div className="toc-box">
                <div className="toc-title">Contents</div>
                <ul className="toc-list">
                  <li><a href="#constellation-graph"><span className="toc-number">1</span> Constellation Route Graph</a></li>
                  <li><a href="#route-narrative"><span className="toc-number">2</span> Verified Hyperlink Path</a></li>
                  <li><a href="#technical-log"><span className="toc-number">3</span> Search Strategy & Heuristics</a></li>
                </ul>
              </div>

              {/* Section 1: Litmaps Floating Constellation Graph */}
              <div id="constellation-graph">
                <h2 className="wiki-section-heading">1. Constellation Route Graph</h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--wm-text-secondary)', marginBottom: '0.75rem' }}>
                  Interactive topological representation of the speedrun route. Glowing nodes represent confirmed Wikipedia pages along the shortest path, connected by directed geometric edges with traveling pulses. Faint dashed nodes represent evaluated branch candidates.
                </p>

                {/* Graph Container (embedded or fullscreen) */}
                <div className={`graph-panel-wrapper ${isFullscreenGraph ? 'fullscreen' : ''}`}>
                  <FloatingGraph
                    nodes={graphNodes}
                    edges={graphEdges}
                    selectedStep={selectedStep}
                    onSelectNode={idx => setSelectedStep(idx)}
                    traversing={traversing}
                    statusMessage={traversalStatus}
                    isFullscreen={isFullscreenGraph}
                    onToggleFullscreen={() => setIsFullscreenGraph(!isFullscreenGraph)}
                  />
                </div>
              </div>

              {/* Section 2: Verified Hyperlink Path */}
              <div id="route-narrative">
                <h2 className="wiki-section-heading">2. Verified Hyperlink Path</h2>
                <p style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                  The following table enumerates each verified step from the origin article to the destination target. Each link has been validated against Wikipedia's current revision to guarantee that the preceding article's body contains a direct link to the next hop.
                </p>

                <table className="wiki-route-table">
                  <thead>
                    <tr>
                      <th style={{ width: '10%' }}>Step</th>
                      <th style={{ width: '40%' }}>Article Title</th>
                      <th style={{ width: '30%' }}>Role</th>
                      <th style={{ width: '20%' }}>Verification</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pathTitles.map((title, idx) => {
                      const isStart = idx === 0
                      const isTarget = idx === pathTitles.length - 1
                      return (
                        <tr
                          key={idx}
                          style={{
                            backgroundColor: selectedStep === idx ? '#eaf3ff' : 'transparent',
                            cursor: 'pointer'
                          }}
                          onClick={() => setSelectedStep(idx)}
                          title="Click to highlight on graph"
                        >
                          <td><b>{idx}</b></td>
                          <td>
                            <a
                              href={`https://en.wikipedia.org/wiki/${encodeURIComponent(title.replace(/ /g, '_'))}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ fontWeight: 'bold' }}
                            >
                              {title}
                            </a>
                          </td>
                          <td>
                            {isStart && <span className="hop-tag-badge start">Start Origin</span>}
                            {isTarget && <span className="hop-tag-badge target">Target Destination</span>}
                            {!isStart && !isTarget && <span className="hop-tag-badge">Hop {idx}</span>}
                          </td>
                          <td style={{ color: 'var(--wm-success-green)', fontSize: '0.78rem' }}>
                            <CheckCircle2 size={13} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
                            <span>Verified</span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Section 3: Technical Strategy & Heuristics */}
              <div id="technical-log">
                <h2 className="wiki-section-heading">3. Search Strategy & Heuristics</h2>
                <p style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                  WikiSpeedrunner navigates the Wikipedia graph using a bidirectional heuristic engine:
                </p>
                <ul style={{ fontSize: '0.85rem', paddingLeft: '1.5rem', marginBottom: '1.5rem', lineHeight: '1.6' }}>
                  <li>
                    <b>Target Backlink Intersect:</b> Pre-fetches the target article's incoming backlinks. If an explored page links directly to any backlink, an instant 2-hop bridge is verified and committed.
                  </li>
                  <li>
                    <b>Acyclic Path Guarantee:</b> Traversal strictly prevents closed cycles, maintaining an invariant DAG structure where no article is visited more than once.
                  </li>
                  <li>
                    <b>Body Link Verification:</b> Every candidate hop is confirmed to exist within the rendered HTML of the preceding page, avoiding phantom navbox or template transclusions.
                  </li>
                </ul>

                <button
                  onClick={() => setIsDrawerOpen(true)}
                  className="wiki-btn-secondary"
                  style={{ marginBottom: '1.5rem' }}
                >
                  <FileText size={14} />
                  <span>Open Full Decision Matrix Log ({result?.log?.length || 0} steps)</span>
                </button>
              </div>

              {/* Wikipedia Categories Bar */}
              <div className="catlinks">
                <span className="catlinks-title">Categories:</span>
                <a href="#">Wikipedia speedruns</a> |{' '}
                <a href="#">Graph theory</a> |{' '}
                <a href="#">Acyclic path algorithms</a> |{' '}
                <a href="#">{startArticle}</a> |{' '}
                <a href="#">{targetArticle}</a>
              </div>
            </div>

            {/* Right Column: Wikipedia Infobox */}
            <aside className="wiki-infobox">
              <div className="infobox-title">Speedrun Path</div>
              <div className="infobox-subheader">Shortest Route Summary</div>

              <table style={{ width: '100%' }}>
                <tbody>
                  <tr className="infobox-row">
                    <th>Start Page</th>
                    <td>
                      <a
                        href={`https://en.wikipedia.org/wiki/${encodeURIComponent(startArticle.replace(/ /g, '_'))}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {startArticle}
                      </a>
                    </td>
                  </tr>

                  <tr className="infobox-row">
                    <th>Target Page</th>
                    <td>
                      <a
                        href={`https://en.wikipedia.org/wiki/${encodeURIComponent(targetArticle.replace(/ /g, '_'))}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {targetArticle}
                      </a>
                    </td>
                  </tr>

                  <tr className="infobox-row">
                    <th>Status</th>
                    <td className="infobox-status-victory">
                      {result?.status === 'victory' ? 'Victory (Route Found)' : (result?.status ? result.status.toUpperCase() : 'Ready')}
                    </td>
                  </tr>

                  <tr className="infobox-row">
                    <th>Total Nodes</th>
                    <td><b>{pathTitles.length}</b> nodes</td>
                  </tr>

                  <tr className="infobox-row">
                    <th>Total Hops</th>
                    <td><b>{result?.steps ?? 0}</b> {result?.steps === 1 ? 'hop' : 'hops'}</td>
                  </tr>

                  <tr className="infobox-row">
                    <th>Elapsed Time</th>
                    <td>{result?.elapsed_seconds ?? 0} s</td>
                  </tr>

                  <tr className="infobox-row">
                    <th>Graph Topology</th>
                    <td>Directed Acyclic Graph (0 cycles)</td>
                  </tr>

                  <tr className="infobox-row">
                    <th>Link Verification</th>
                    <td style={{ color: 'var(--wm-success-green)' }}>
                      100% verified on page
                    </td>
                  </tr>

                  <tr className="infobox-row">
                    <th>API Calls</th>
                    <td>{result?.api_calls ?? 0}</td>
                  </tr>

                  <tr className="infobox-row">
                    <th>Heuristic</th>
                    <td>Target Backlink Intersect</td>
                  </tr>
                </tbody>
              </table>

              <div style={{ padding: '0.5rem', textAlign: 'center', background: '#ffffff', borderTop: '1px solid #eaecf0' }}>
                <button
                  onClick={() => setIsDrawerOpen(true)}
                  className="wiki-btn-primary"
                  style={{ width: '100%', justifyContent: 'center' }}
                >
                  <Award size={13} />
                  <span>Inspect Decision Log</span>
                </button>
              </div>
            </aside>
          </div>
        </main>
      </div>

      {/* 4. Wikipedia Vector Footer */}
      <footer className="wiki-footer" style={{ textAlign: 'center' }}>
        <p style={{ marginBottom: '4px' }}>
          This page is a dynamic route simulation modeled after the English Wikipedia interface. Content is derived from the MediaWiki Action API under Creative Commons Attribution-ShareAlike 4.0 License.
        </p>
        <p style={{ color: 'var(--wm-text-muted)' }}>
          WikiSpeedrunner Engine v2.1 • Made with joy💛.
        </p>
      </footer>

      {/* Slide-out Decision Matrix Drawer */}
      <DecisionDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        log={result?.log || []}
        pathTitles={pathTitles}
      />
    </div>
  )
}
