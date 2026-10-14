import { useEffect, useState, type FormEvent } from 'react'
import { NavLink } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import {
  getPredictionTrace,
  getResearchAblations,
  getResearchCalibration,
  getResearchConfusion,
  getResearchCurves,
  getResearchColdStart,
  getResearchEvaluation,
  getResearchModel,
  getResearchPredictions,
  getResearchSeeds,
} from '../api/research'
import {
  getDatabaseInspection,
  getShowcaseStatus,
  resetShowcase,
  seedShowcase,
  type DatabaseInspection,
  type ShowcaseStatus,
} from '../api/showcase'
import { Card, PageHeader } from '../components'
import { mistakeLabels } from '../constants/errorLabels'
import type { ErrorType } from '../types/entities'

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.'

export function ResearchPage({
  mode,
}: {
  mode: 'overview' | 'formula' | 'evaluation' | 'formula-explorer' | 'analytics' | 'predictions' | 'comparisons' | 'showcase'
}) {
  const { student, user } = useStudent()
  const studentId = student?.id ?? user?.student_id ?? (typeof (user as any)?.id === 'number' ? (user as any).id : 1)

  const [model, setModel] = useState<Record<string, any> | null>(null)
  const [evaluation, setEvaluation] = useState<Record<string, any> | null>(null)
  const [ablations, setAblations] = useState<Record<string, any> | null>(null)
  const [seeds, setSeeds] = useState<Record<string, any> | null>(null)
  const [curves, setCurves] = useState<Record<string, any> | null>(null)
  const [coldStart, setColdStart] = useState<Record<string, any> | null>(null)
  const [calibration, setCalibration] = useState<Record<string, any> | null>(null)
  const [confusion, setConfusion] = useState<Record<string, any> | null>(null)
  const [evaluationModel, setEvaluationModel] = useState('mistiq-ampa')
  const [evaluationSeed, setEvaluationSeed] = useState('42')
  const [comparisonModel, setComparisonModel] = useState('all')
  const [ablationFilter, setAblationFilter] = useState('all')
  const [predictions, setPredictions] = useState<Record<string, any>[]>([])
  const [lookupStudentId, setLookupStudentId] = useState(String(studentId || 1))
  const [predictionId, setPredictionId] = useState('')
  const [trace, setTrace] = useState<Record<string, any> | null>(null)
  const [showcaseStatus, setShowcaseStatus] = useState<ShowcaseStatus | null>(null)
  const [inspection, setInspection] = useState<DatabaseInspection | null>(null)
  const [showcaseBusy, setShowcaseBusy] = useState(false)
  const [showcaseNotice, setShowcaseNotice] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getResearchModel()
      .then(m => { if (active) setModel(m) })
      .catch(reason => { if (active) setError(errorMessage(reason)) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (mode !== 'formula' && mode !== 'formula-explorer') return
    let active = true
    const targetStudentId = Number(lookupStudentId) || 1
    getResearchPredictions(targetStudentId)
      .then(rows => {
        if (!active) return
        setPredictions(rows)
        if (rows[0] && !predictionId) {
          setPredictionId(String(rows[0].id))
          return getPredictionTrace(rows[0].id)
        }
      })
      .then(t => {
        if (active && t) setTrace(t)
      })
      .catch(() => undefined)
    return () => { active = false }
  }, [mode, lookupStudentId])

  useEffect(() => {
    if (mode !== 'showcase') return
    let active = true
    Promise.all([getShowcaseStatus(), getDatabaseInspection()])
      .then(([status, query]) => {
        if (active) {
          setShowcaseStatus(status)
          setInspection(query)
        }
      })
      .catch(reason => { if (active) setError(errorMessage(reason)) })
    return () => { active = false }
  }, [mode])

  useEffect(() => {
    if (mode !== 'evaluation') return
    let active = true
    Promise.all([
      getResearchEvaluation(),
      getResearchAblations(),
      getResearchSeeds(),
      getResearchCurves(),
      getResearchColdStart(),
    ])
      .then(([e, a, s, c, cold]) => {
        if (active) {
          setEvaluation(e)
          setAblations(a)
          setSeeds(s)
          setCurves(c)
          setColdStart(cold)
        }
      })
      .catch(reason => { if (active) setError(errorMessage(reason)) })
    return () => { active = false }
  }, [mode])

  useEffect(() => {
    if (mode !== 'evaluation') return
    let active = true
    Promise.all([
      getResearchCalibration(evaluationModel, Number(evaluationSeed)),
      getResearchConfusion(evaluationModel, Number(evaluationSeed)),
    ])
      .then(([cal, conf]) => {
        if (active) {
          setCalibration(cal)
          setConfusion(conf)
        }
      })
      .catch(reason => { if (active) setError(errorMessage(reason)) })
    return () => { active = false }
  }, [mode, evaluationModel, evaluationSeed])

  const loadPredictions = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setTrace(null)
    setPredictions([])
    setPredictionId('')
    try {
      const rows = await getResearchPredictions(Number(lookupStudentId))
      setPredictions(rows)
      if (rows[0]) {
        setPredictionId(String(rows[0].id))
        setTrace(await getPredictionTrace(rows[0].id))
      }
    } catch (reason) {
      setError(errorMessage(reason))
    }
  }

  const loadTrace = async () => {
    if (!predictionId) return
    setError('')
    try {
      setTrace(await getPredictionTrace(Number(predictionId)))
    } catch (reason) {
      setError(errorMessage(reason))
    }
  }

  const runShowcaseAction = async (action: 'reset' | 'seed') => {
    setShowcaseBusy(true)
    setShowcaseNotice('')
    setError('')
    try {
      if (action === 'reset') {
        await resetShowcase()
        setShowcaseNotice('Reset complete. The demo student has no practice history until it is seeded.')
      } else {
        await seedShowcase()
        setShowcaseNotice('Seed complete. The demo session was replayed through the live AMPA pipeline.')
      }
      const [status, query] = await Promise.all([getShowcaseStatus(), getDatabaseInspection()])
      setShowcaseStatus(status)
      setInspection(query)
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setShowcaseBusy(false)
    }
  }

  const titles = {
    overview: ['Research / Model Lab', 'Implementation and saved model details from this project.'],
    formula: ['Formula Explorer', 'Reconstruct a stored prediction from its attempt history and saved AMPA parameters.'],
    'formula-explorer': ['Formula Explorer', 'Reconstruct a stored prediction from its attempt history and saved AMPA parameters.'],
    analytics: ['Analytics', 'Advanced analytics artifacts.'],
    predictions: ['Predictions', 'Research prediction view.'],
    comparisons: ['Comparisons', 'Comparisons of models/approaches.'],
    evaluation: ['Evaluation', 'Phase 4 evaluation artifacts, read directly from experiment outputs.'],
    showcase: ['Database Inspector', 'Live view of the local MISTIQ application database.'],
  } as const

  const [title, description] = titles[mode] || titles.overview
  const metricKeys = [
    'accuracy',
    'macro_precision',
    'macro_recall',
    'macro_f1',
    'weighted_f1',
    'log_loss',
    'top2_accuracy',
    'top3_accuracy',
    'brier_score',
    'ece',
  ]
  const fmt = (v: unknown) => (typeof v === 'number' ? v.toFixed(4) : String(v ?? '—'))

  return (
    <>
      <PageHeader title={title} description={description} />

      <div className="research-links research-tabs">
        <NavLink to="/research" end>Research overview</NavLink>
        <NavLink to="/research/showcase">Database</NavLink>
        <NavLink to="/research/formula-explorer">Formula explorer</NavLink>
        <NavLink to="/research/evaluation">Evaluation</NavLink>
      </div>

      <div className="showcase-disclosure">
        <span className="badge badge-accent">Showcase Mode · Synthetic Data</span>
        <span>
          Research evaluation uses synthetic data. Results demonstrate the current implementation and experimental setup, not validated real-world educational effectiveness.
        </span>
      </div>

      {error && <p className="error research-error" role="alert">{error}</p>}

      {mode === 'overview' && (
        <div className="research-grid">
          <Card className="research-wide">
            <div className="card-kicker">MISTIQ-AMPA · {model?.model_version ?? '…'}</div>
            <h2>Adaptive Mistake Propagation Algorithm</h2>
            <p>
              Predicts a likely next mistake category from sequential learning behavior. It is a project-specific custom sequential mistake-prediction framework, not a claimed universal machine-learning paradigm.
            </p>
            <div className="research-facts">
              <span>Features<strong>{model?.feature_count ?? '—'}</strong></span>
              <span>Classes<strong>{model?.class_count ?? '—'}</strong></span>
              <span>Training<strong>{model?.training_status ?? '—'}</strong></span>
              <span>Evaluation<strong>{model?.evaluation_status ?? '—'}</strong></span>
            </div>
          </Card>

          <Card className="research-wide">
            <div className="card-kicker">IMPLEMENTED PIPELINE</div>
            <div className="research-pipeline">
              {[
                'Student attempts',
                'Mistake events',
                'Mistake memory',
                'Feature engineering',
                'Risk representation',
                'AMPA scores',
                'Stable softmax',
                'Prediction and explanation',
                'Recommendation',
              ].map((item, i) => (
                <div key={item}>
                  <span>{String(i + 1).padStart(2, '0')}</span>
                  {item}
                </div>
              ))}
            </div>
          </Card>

          <Card className="research-wide">
            <div className="card-kicker">FEATURES FROM THE MODEL IMPLEMENTATION</div>
            <div className="research-feature-grid">
              {(model?.feature_definitions ?? []).map((feature: Record<string, any>) => (
                <article key={feature.name}>
                  <div>
                    <strong>{feature.label ?? feature.name.replaceAll('_', ' ')}</strong>
                    <code>{feature.symbol}</code>
                  </div>
                  <p>{feature.description}</p>
                  <small>Range {feature.range}. {feature.role}</small>
                </article>
              ))}
            </div>
            <p className="research-note">
              The model transforms learning stability to instability (1 − stability) before standardization and scoring. Student profile labels are computational learning-history signals, not psychological attributes.
            </p>
          </Card>
        </div>
      )}

      {mode === 'showcase' && (
        <div className="research-stack">
          <Card>
            <div className="card-kicker">DATABASE INSPECTOR</div>
            <h2>Demo student session</h2>
            <p>
              All analytics, predictions and recommendations come from the live pipeline over the local application database. Reset clears a student's history; seed replays a curated session through the same <code>POST /attempts</code> path the app uses.
            </p>
            <div className="research-facts">
              <span>Status<strong>{showcaseStatus?.seeded ? 'Seeded' : 'Empty'}</strong></span>
              <span>Attempts<strong>{showcaseStatus?.attempt_count ?? '—'}</strong></span>
              <span>Mistakes<strong>{showcaseStatus?.mistake_count ?? '—'}</strong></span>
              <span>Prediction<strong>{showcaseStatus?.latest_prediction_error ?? '—'}</strong></span>
            </div>
            <div className="research-form">
              <button className="button" onClick={() => runShowcaseAction('seed')} disabled={showcaseBusy}>
                {showcaseBusy ? 'Working…' : 'Seed demo session'}
              </button>
              <button className="button button-secondary" onClick={() => runShowcaseAction('reset')} disabled={showcaseBusy}>
                Reset demo history
              </button>
            </div>
            {showcaseNotice && <p className="research-note">{showcaseNotice}</p>}
          </Card>

          <div className="research-split">
            <Card>
              <div className="card-kicker">LIVE DATABASE PROOF</div>
              <p>Row counts and the latest writes in the normal local database (<code>mistiq.db</code>) that powers this session.</p>
              {inspection?.counts ? (
                <div className="research-facts">
                  <span>Students<strong>{inspection.counts.students}</strong></span>
                  <span>Questions<strong>{inspection.counts.questions}</strong></span>
                  <span>Attempts<strong>{inspection.counts.attempts}</strong></span>
                  <span>Predictions<strong>{inspection.counts.predictions}</strong></span>
                  <span>Recommendations<strong>{inspection.counts.recommendations}</strong></span>
                  <span>Mistake events<strong>{inspection.counts.mistake_events}</strong></span>
                </div>
              ) : (
                <p className="analytics-empty">Inspecting…</p>
              )}
            </Card>

            <Card>
              <div className="card-kicker">LATEST LIVE WRITES</div>
              {inspection?.latest_attempt ? (
                <ul className="insight-list">
                  <li>
                    <div>
                      <strong>Attempt #{inspection.latest_attempt.attempt_id}</strong>
                      <span>Question {inspection.latest_attempt.question_id} · {inspection.latest_attempt.correct ? 'correct' : 'incorrect'}</span>
                      <small>{new Date(inspection.latest_attempt.timestamp).toLocaleString()}</small>
                    </div>
                  </li>
                  <li>
                    <div>
                      <strong>Mistake #{inspection.latest_mistake?.mistake_event_id}</strong>
                      <span>{inspection.latest_mistake?.topic} · {mistakeLabels[inspection.latest_mistake?.error_type as ErrorType] ?? inspection.latest_mistake?.error_type}</span>
                      <small>{inspection.latest_mistake ? new Date(inspection.latest_mistake.timestamp).toLocaleString() : '—'}</small>
                    </div>
                  </li>
                  <li>
                    <div>
                      <strong>Prediction #{inspection.latest_prediction?.id}</strong>
                      <span>
                        {inspection.latest_prediction?.predicted_error} · {((inspection.latest_prediction?.probability ?? 0) * 100).toFixed(1)}% · {inspection.latest_prediction?.status}
                      </span>
                      <small>{inspection.latest_prediction ? new Date(inspection.latest_prediction.created_at).toLocaleString() : '—'}</small>
                    </div>
                  </li>
                </ul>
              ) : (
                <p className="analytics-empty">No writes recorded yet.</p>
              )}
            </Card>
          </div>
        </div>
      )}

      {(mode === 'formula' || mode === 'formula-explorer') && (
        <div className="research-stack">
          <Card>
            <div className="card-kicker">SELECT HISTORICAL CONTEXT</div>
            <form className="research-form" onSubmit={loadPredictions}>
              <label>
                Student ID
                <input
                  value={lookupStudentId}
                  onChange={e => setLookupStudentId(e.target.value)}
                  required
                  type="number"
                  min="1"
                />
              </label>
              <button className="button" type="submit">Load predictions</button>
            </form>

            {predictions.length > 0 && (
              <div className="research-form">
                <label>
                  Prediction
                  <select
                    value={predictionId}
                    onChange={e => {
                      setPredictionId(e.target.value)
                    }}
                  >
                    {predictions.map(p => (
                      <option value={p.id} key={p.id}>
                        #{p.id} · {p.prediction} · {p.timestamp}
                      </option>
                    ))}
                  </select>
                </label>
                <button className="button" onClick={loadTrace}>Trace calculation</button>
              </div>
            )}
            {predictions.length === 0 && (
              <p className="research-note">Enter a student ID and load stored predictions.</p>
            )}
          </Card>

          {model && (
            <Card>
              <div className="card-kicker">IMPLEMENTED FEATURE PARAMETERS</div>
              <p>
                Memory: recency weight exp(−λ · age days), λ={fmt(model.hyperparameters?.decay_rate)}; repetition A(N)=1+α log(1+N), α={fmt(model.hyperparameters?.repetition_alpha)}; bounded memory scale={fmt(model.hyperparameters?.memory_scale)}.
              </p>
              <p>
                Momentum compares two windows of k={model.hyperparameters?.momentum_window} interactions with scale={fmt(model.hyperparameters?.momentum_scale)}. Scoring normalization and saved training parameters come from model version {model.model_version}.
              </p>
            </Card>
          )}

          {trace && (
            <>
              <Card>
                <div className="card-kicker">FEATURE SNAPSHOT</div>
                <p>
                  Context: {trace.context?.topic} / {trace.context?.subtopic ?? '—'} · difficulty {trace.context?.difficulty} · attempts replayed {trace.attempt_count}. Raw history features and standardized scoring values are shown separately.
                </p>
                <div className="research-table-wrap">
                  <table className="research-table">
                    <thead>
                      <tr>
                        <th>Class</th>
                        {(model?.features ?? []).map((f: string) => (
                          <th key={f}>{f}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {trace.classes?.map((label: string) => (
                        <tr
                          key={label}
                          className={trace.prediction?.predicted_error === label ? 'trace-predicted' : ''}
                        >
                          <th>{label}</th>
                          {(model?.features ?? []).map((f: string) => (
                            <td key={f}>{fmt(trace.scoring_features_by_class?.[label]?.[f])}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card>
                <div className="card-kicker">LEARNED WEIGHTS AND BIAS · {trace.model_version}</div>
                <div className="research-table-wrap">
                  <table className="research-table">
                    <thead>
                      <tr>
                        <th>Class</th>
                        {(model?.features ?? []).map((f: string) => (
                          <th key={f}>{f}</th>
                        ))}
                        <th>Bias</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trace.classes?.map((label: string, i: number) => (
                        <tr
                          key={label}
                          className={trace.prediction?.predicted_error === label ? 'trace-predicted' : ''}
                        >
                          <th>{label}</th>
                          {(model?.features ?? []).map((_: string, j: number) => (
                            <td key={j}>{fmt(trace.weights?.[i]?.[j])}</td>
                          ))}
                          <td>{fmt(trace.bias?.[i])}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card>
                <div className="card-kicker">SELECTED CLASS SCORE · {trace.prediction?.predicted_error ?? 'NO RELIABLE PREDICTION'}</div>
                <p>
                  For each class z = b + ∑(weight × standardized feature). Contributions below are the actual selected class feature × learned weight.
                </p>
                <div className="research-table-wrap">
                  <table className="research-table">
                    <thead>
                      <tr>
                        <th>Feature</th>
                        <th>Value</th>
                        <th>Weight</th>
                        <th>Contribution</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(trace.contributions ?? []).map((r: Record<string, any>) => (
                        <tr key={r.feature}>
                          <th>{r.label}</th>
                          <td>{fmt(r.value)}</td>
                          <td>{fmt(r.weight)}</td>
                          <td>{fmt(r.contribution)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p>
                  Bias: {fmt(trace.bias?.[trace.classes?.indexOf(trace.prediction?.predicted_error)])} · Raw score: {fmt(trace.raw_scores?.[trace.prediction?.predicted_error])}
                </p>
              </Card>

              <Card>
                <div className="card-kicker">STABLE SOFTMAX AND OUTCOME</div>
                <div className="research-table-wrap">
                  <table className="research-table">
                    <thead>
                      <tr>
                        <th>Class</th>
                        <th>Raw z</th>
                        <th>z − max(z)</th>
                        <th>exp(shifted z)</th>
                        <th>Probability</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trace.classes?.map((label: string) => (
                        <tr
                          key={label}
                          className={trace.prediction?.predicted_error === label ? 'trace-predicted' : ''}
                        >
                          <th>{label}</th>
                          <td>{fmt(trace.raw_scores?.[label])}</td>
                          <td>{fmt(trace.shifted_scores?.[label])}</td>
                          <td>{fmt(trace.exponentials?.[label])}</td>
                          <td>{fmt(trace.probabilities?.[label])}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p>
                  Prediction: <strong>{trace.prediction?.predicted_error ?? 'No reliable prediction'}</strong> · Probability {fmt(trace.prediction?.probability)} · Confidence {fmt(trace.prediction?.confidence)} · Data reliability {fmt(trace.prediction?.data_reliability)}
                </p>
                <p className="research-note">
                  Confidence is probability × data reliability. Reliability summarizes history volume, topic relevance, concept coverage, and consistency. Trace verification: {trace.verification_status}.
                </p>
              </Card>
            </>
          )}
        </div>
      )}

      {mode === 'evaluation' && (
        <div className="research-stack">
          <Card>
            <div className="card-kicker">EXPERIMENT SELECTOR</div>
            <div className="research-form">
              <label>
                Comparison model
                <select value={comparisonModel} onChange={e => setComparisonModel(e.target.value)}>
                  <option value="all">All models</option>
                  {[...new Set((evaluation?.results ?? []).map((r: Record<string, any>) => r.model_name))].map((x: any) => (
                    <option key={x} value={x}>{x}</option>
                  ))}
                </select>
              </label>
              <label>
                Ablation
                <select value={ablationFilter} onChange={e => setAblationFilter(e.target.value)}>
                  <option value="all">All ablations</option>
                  {[...new Set((ablations?.results ?? []).map((r: Record<string, any>) => r.removed_feature).filter(Boolean))].map((x: any) => (
                    <option key={x} value={x}>{x}</option>
                  ))}
                </select>
              </label>
              <label>
                Calibration / confusion model
                <select value={evaluationModel} onChange={e => setEvaluationModel(e.target.value)}>
                  {['mistiq-ampa', 'majority', 'logistic_regression', 'decision_tree', 'random_forest', 'knn'].map(x => (
                    <option key={x} value={x}>{x.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </label>
              <label>
                Seed
                <select value={evaluationSeed} onChange={e => setEvaluationSeed(e.target.value)}>
                  <option value="42">42</option>
                  <option value="123">123</option>
                </select>
              </label>
            </div>
          </Card>

          <Card>
            <div className="card-kicker">MODEL COMPARISON · {evaluation?.source ?? 'Loading'}</div>
            {evaluation?.available ? (
              <div className="research-table-wrap">
                <table className="research-table">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Seed</th>
                      {metricKeys.map(k => (
                        <th key={k}>{k.replace(/_/g, ' ')}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {evaluation.results
                      .filter((row: Record<string, any>) => comparisonModel === 'all' || row.model_name === comparisonModel)
                      .map((row: Record<string, any>, i: number) => (
                        <tr key={`${row.model_name}-${row.seed}-${i}`}>
                          <th>{row.model_name}</th>
                          <td>{row.seed}</td>
                          {metricKeys.map(k => (
                            <td key={k}>{fmt(Number(row[k]))}</td>
                          ))}
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>No Phase 4 comparison results are present in the configured artifact.</p>
            )}
          </Card>

          <Card>
            <div className="card-kicker">ABLATION RESULTS · {ablations?.source}</div>
            {ablations?.available ? (
              <>
                <p>
                  ΔF1 is the ablation seed score minus the available full AMPA aggregate mean; the comparison file does not contain per-seed full model scores.
                </p>
                <div className="research-table-wrap">
                  <table className="research-table">
                    <thead>
                      <tr>
                        <th>Experiment</th>
                        <th>Seed</th>
                        <th>Macro F1</th>
                        <th>ΔF1 vs full AMPA mean</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ablations.results
                        .filter((row: Record<string, any>) => ablationFilter === 'all' || row.removed_feature === ablationFilter)
                        .map((row: Record<string, any>, i: number) => {
                          const base = evaluation?.results?.find(
                            (candidate: Record<string, any>) =>
                              candidate.model_name === 'MISTIQ-AMPA' && String(candidate.seed) === 'mean'
                          )
                          return (
                            <tr key={`${row.experiment_id}-${i}`}>
                              <th>{row.model_name}</th>
                              <td>{row.seed}</td>
                              <td>{fmt(Number(row.macro_f1))}</td>
                              <td>{base ? fmt(Number(row.macro_f1) - Number(base.macro_f1)) : '—'}</td>
                            </tr>
                          )
                        })}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p>No ablation output is available.</p>
            )}
          </Card>

          <div className="research-split">
            <Card>
              <div className="card-kicker">CALIBRATION · seed {calibration?.seed}</div>
              {calibration?.available ? (
                <>
                  <p>Brier {fmt(calibration.result?.brier_score)} · ECE {fmt(calibration.result?.ece)}</p>
                  {calibration.result?.bins?.map((bin: Record<string, any>) => (
                    <div className="research-bin" key={bin.bin}>
                      <span>{Number(bin.lower).toFixed(1)}–{Number(bin.upper).toFixed(1)}</span>
                      <div>
                        <i style={{ width: `${Math.min(100, bin.mean_confidence * 100)}%` }} />
                        <b style={{ left: `${Math.min(100, bin.accuracy * 100)}%` }} />
                      </div>
                      <small>n={bin.count}; confidence {fmt(bin.mean_confidence)}; accuracy {fmt(bin.accuracy)}</small>
                    </div>
                  ))}
                </>
              ) : (
                <p>Calibration artifact is not available.</p>
              )}
            </Card>

            <Card>
              <div className="card-kicker">CONFUSION MATRIX · seed {confusion?.seed}</div>
              {confusion?.available ? (
                <div className="research-table-wrap">
                  <table className="research-table">
                    <thead>
                      <tr>
                        <th>Actual \ Predicted</th>
                        {confusion.result?.labels?.map((x: string) => (
                          <th key={x}>{x}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {confusion.result?.matrix?.map((row: number[], i: number) => (
                        <tr key={i}>
                          <th>{confusion.result?.labels?.[i]}</th>
                          {row.map((value, j) => (
                            <td key={j}>{value}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>Confusion matrix is not available for this selection.</p>
              )}
            </Card>
          </div>

          <Card>
            <div className="card-kicker">SEED ROBUSTNESS</div>
            {seeds?.available ? (
              <div className="research-table-wrap">
                <table className="research-table">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Metric</th>
                      <th>Mean</th>
                      <th>SD</th>
                      <th>Min</th>
                      <th>Max</th>
                      <th>Seeds</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(seeds.results).flatMap(([name, metrics]: [string, any]) =>
                      Object.entries(metrics).map(([metric, stats]: [string, any]) => (
                        <tr key={`${name}-${metric}`}>
                          <th>{name}</th>
                          <td>{metric}</td>
                          <td>{fmt(stats.mean)}</td>
                          <td>{fmt(stats.std)}</td>
                          <td>{fmt(stats.min)}</td>
                          <td>{fmt(stats.max)}</td>
                          <td>{stats.seeds}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>Seed robustness results are unavailable.</p>
            )}
          </Card>

          <Card>
            <div className="card-kicker">LEARNING CURVES</div>
            {curves?.available && curves.results?.length ? (
              <div className="research-table-wrap">
                <table className="research-table">
                  <thead>
                    <tr>
                      <th>History attempts</th>
                      <th>Seed</th>
                      <th>Sample count</th>
                      <th>Macro F1</th>
                      <th>Accuracy</th>
                      <th>ECE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {curves.results.map((r: Record<string, any>, i: number) => (
                      <tr key={i}>
                        <th>{r.history_attempts}</th>
                        <td>{r.seed}</td>
                        <td>{r.sample_count}</td>
                        <td>{fmt(r.metrics?.macro_f1)}</td>
                        <td>{fmt(r.metrics?.accuracy)}</td>
                        <td>{fmt(r.metrics?.ece)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>Learning-curve result file is unavailable or empty.</p>
            )}
          </Card>

          <Card>
            <div className="card-kicker">COLD-START PERFORMANCE</div>
            {coldStart?.available && coldStart.results?.length ? (
              <div className="research-table-wrap">
                <table className="research-table">
                  <thead>
                    <tr>
                      <th>History bucket</th>
                      <th>Seed</th>
                      <th>Policy</th>
                      <th>Samples</th>
                      <th>Status</th>
                      <th>Macro F1</th>
                      <th>Log loss</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coldStart.results.map((r: Record<string, any>, i: number) => (
                      <tr key={i}>
                        <th>{r.history_bucket}</th>
                        <td>{r.seed}</td>
                        <td>{r.confidence_policy}</td>
                        <td>{r.sample_count}</td>
                        <td>{r.status}</td>
                        <td>{r.metrics ? fmt(r.metrics.macro_f1) : 'Not scored'}</td>
                        <td>{r.metrics ? fmt(r.metrics.log_loss) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>Cold-start analysis is unavailable.</p>
            )}
            <p className="research-note">
              AMPA confidence policy abstains from a reliable class prediction at four or fewer attempts. Small history buckets may contain too few held-out examples for performance estimates.
            </p>
          </Card>
        </div>
      )}
    </>
  )
}
