import React from 'react'
import { X, ExternalLink, ArrowRight, Award } from 'lucide-react'

export default function DecisionDrawer({ isOpen, onClose, log = [], pathTitles = [] }) {
  if (!isOpen) return null

  return (
    <div className="wiki-decision-drawer">
      <div className="decision-drawer-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Award size={18} color="#3366cc" />
          <h3 className="decision-drawer-title">Speedrun Decision Matrix</h3>
        </div>
        <button
          onClick={onClose}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#54595d' }}
          title="Close drawer"
        >
          <X size={18} />
        </button>
      </div>

      <div className="decision-drawer-content">
        {log.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#72777d', padding: '2rem 1rem' }}>
            No decision steps logged yet. Run a speedrun to inspect candidate evaluation!
          </div>
        ) : (
          log.map((entry, idx) => {
            const stepNum = entry.step || (idx + 1)
            const curr = entry.current_title || entry.current || ''
            const chosen = entry.chosen_title || entry.chosen || ''
            const strategy = entry.strategy || 'HEURISTIC_SEARCH'
            const score = entry.score || 0.0
            const topCandidates = entry.top_candidates || []

            return (
              <div key={idx} className="decision-card">
                <div className="decision-card-top">
                  <span style={{ color: '#3366cc' }}>Step {stepNum}</span>
                  <span style={{ color: '#008529', fontSize: '0.75rem' }}>Score: {score.toFixed(2)}</span>
                </div>

                <div style={{ fontSize: '0.88rem', fontWeight: 'bold', margin: '4px 0', display: 'flex', alignItems: 'center' }}>
                  <span>{curr}</span>
                  <ArrowRight size={13} style={{ margin: '0 6px', color: '#72777d' }} />
                  <span style={{ color: '#0b0080' }}>{chosen}</span>
                </div>

                <div style={{ fontSize: '0.72rem', color: '#54595d', marginBottom: '6px' }}>
                  Strategy: <code style={{ background: '#eaecf0', padding: '1px 4px', borderRadius: '2px' }}>{strategy}</code>
                </div>

                {topCandidates.length > 0 && (
                  <div style={{ background: '#ffffff', border: '1px solid #eaecf0', padding: '6px', borderRadius: '2px', marginTop: '6px' }}>
                    <div style={{ fontWeight: '600', marginBottom: '4px', fontSize: '0.7rem', color: '#54595d' }}>
                      Top Evaluated Candidates:
                    </div>
                    {topCandidates.slice(0, 4).map((c, cIdx) => (
                      <div key={cIdx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', padding: '2px 0' }}>
                        <span style={{ color: '#202122' }}>{c.title || c.text || ''}</span>
                        <span style={{ color: '#72777d' }}>
                          {(c.score !== undefined) ? c.score.toFixed(2) : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ marginTop: '6px', textAlign: 'right' }}>
                  <a
                    href={`https://en.wikipedia.org/wiki/${encodeURIComponent(chosen.replace(/ /g, '_'))}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: '0.72rem', color: '#3366cc', display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                  >
                    View on Wikipedia <ExternalLink size={10} />
                  </a>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
