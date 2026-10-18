import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getStudentTelemetry, type TelemetryData } from '../api/predictions'
import { Card, Icon } from '../components'
import { mistakeLabels } from '../constants/errorLabels'

export function MLEngineHUD({ studentId }: { studentId: number }) {
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!studentId) return
    let active = true
    getStudentTelemetry(studentId)
      .then(res => {
        if (active) setTelemetry(res)
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [studentId])

  if (!telemetry || loading) return null

  const topThreeAttributions = Object.entries(telemetry.feature_attributions)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 3)

  return (
    <Card className="ml-engine-hud-card">
      <div className="hud-top-bar">
        <div className="hud-status-badge">
          <span className="pulse-dot-green" />
          <strong className="hud-engine-title">MISTIQ-AMPA ML Engine</strong>
          <span className="hud-status-tag">Active Inference · {telemetry.inference_latency_ms}ms</span>
        </div>
        <Link to="/simulator" className="hud-studio-link">
          Open ML Studio & Simulator <span aria-hidden="true">→</span>
        </Link>
      </div>

      <div className="hud-grid-content">
        <div className="hud-prediction-col">
          <span className="hud-label">Cognitive Failure Diagnosis</span>
          <h4 className="hud-predicted-name">
            {mistakeLabels[telemetry.predicted_error as keyof typeof mistakeLabels] || telemetry.predicted_error}
          </h4>
          <div className="hud-prob-bar-container">
            <div className="hud-prob-fill" style={{ width: `${Math.round(telemetry.probability * 100)}%` }} />
          </div>
          <div className="hud-prob-meta">
            <span>Probability: <strong>{(telemetry.probability * 100).toFixed(0)}%</strong></span>
            <span>Reliability: <strong>{(telemetry.confidence * 100).toFixed(0)}%</strong></span>
            <span>Status: <strong className="status-highlight">{telemetry.status.replace('_', ' ')}</strong></span>
          </div>
        </div>

        <div className="hud-telemetry-col">
          <span className="hud-label">Top Driving Trajectory Signals</span>
          <div className="hud-drivers-list">
            {topThreeAttributions.map(([feature, weight]) => {
              const isPositive = weight >= 0
              const prettyName = feature.replace(/_/g, ' ')
              return (
                <div key={feature} className="hud-driver-item">
                  <span className="hud-driver-name">{prettyName}</span>
                  <span className={`hud-driver-weight ${isPositive ? 'pos-weight' : 'neg-weight'}`}>
                    {isPositive ? `+${weight.toFixed(2)}` : weight.toFixed(2)}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </Card>
  )
}
