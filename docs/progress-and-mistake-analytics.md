# Progress and mistake analytics

Phase 8 reports descriptive values from the student's stored attempts, question metadata, mistake events, and persisted AMPA learner state. These values describe recorded history; they are separate from AMPA's predictive probability and do not modify its math.

## Data and ordering

The services load attempts joined to their questions and optional mistake event in one query per analytics request. Rows are ordered by `(timestamp, attempt_id)`. If a legacy row has no timestamp, its attempt ID supplies a deterministic fallback order; a missing timestamp is not added to the daily/weekly mistake timeline. The database schema normally requires timestamps.

Trajectory points are calculated on each chronological prefix: the point for attempt `n` reads attempts `1..n` only. Cumulative accuracy is correct attempts divided by attempts so far. Per-attempt mistake rate is incorrect attempts divided by attempts so far. Difficulty is the actual question difficulty. Rolling accuracy and mistake rate use the configured trailing attempt window and are null until the configured minimum sample exists. Stability uses the existing AMPA feature from running correct/total counts, so producing all points is linear in the history length and does not recalculate full prefixes.

Current totals, topic/difficulty groupings, and the current persisted learner state use all available history because the API describes the present. Recovery intentionally reads later attempts after each earlier mistake. Therefore, adding future attempts can complete recovery windows and update current aggregates; it cannot change already emitted prefix-only trajectory points.

## Progress metrics

`GET /api/progress/{student_id}` and the compatible `GET /api/students/{student_id}/progress` return the same structured response.

| Metric | Definition and source |
|---|---|
| Overall accuracy | Correct attempts / all attempts. For no attempts, the safe value is `0.0`; the UI displays the empty state instead of presenting it as a result. |
| Recent accuracy | Correct attempts in the latest `N` chronological attempts / observed attempts in that window. Response includes configured window and observed sample size. |
| Improvement | Recent accuracy minus accuracy in the immediately preceding, equally sized attempt window. Direction is `IMPROVING`, `STABLE`, or `DECLINING` using the configured absolute difference threshold. If either window is below the minimum sample, value is null and direction is `INSUFFICIENT_DATA`; both window sample sizes are returned. |
| Current/best streak | Consecutive correct attempt count at the end of the ordered history / maximum such run in that history. |
| Topic/subtopic performance | Attempts, correct/incorrect, accuracy, most-recent-window accuracy, mistake-event count, mean question difficulty, and accuracy trend for actual question topic and subtopic values. A trend uses adjacent equal-sized windows and the same minimum sample rule. |
| Difficulty performance | For levels 1–5, number of attempts, correctness, incorrect-attempt rate, and mean response time from those attempts. Unobserved levels have null rates and zero attempts. |
| High-difficulty success | Correct attempts on levels 4–5 and total attempts on levels 4–5, reported separately. A higher difficulty alone is not described as progress. |
| Learning trajectory | Chronological cumulative accuracy, cumulative mistake-event rate, actual difficulty, AMPA stability feature, and trailing-window values when sufficiently sampled. |

The recent window defaults to 10 attempts; the minimum for comparative trends defaults to 3 observations per window. The stability status reuses persisted `LearnerState.knowledge_stability` or the exact existing AMPA feature calculation when no row exists. Its student-facing status is `STABLE`, `IMPROVING`, `VARIABLE`, or `NEEDS_MORE_DATA`. AMPA signed mistake momentum is reused as stored; it is interpreted as risk increasing/decreasing/stable, not as motivation. Momentum remains unavailable before 10 attempts, matching two default AMPA windows of five events.

## Mistake metrics

The API exposes:

- `GET /api/mistakes/{student_id}`: chronological event list.
- `GET /api/mistakes/{student_id}/summary`: category counts/rates, timeline sufficiency, a recent-event window (up to 20), repeated patterns, and a graph-ready concept confusion network.
- `GET /api/mistakes/{student_id}/repeated`: recurring patterns.
- `GET /api/mistakes/{student_id}/confusions`: observed concepts and confusion edges.
- The existing `GET /api/students/{student_id}/mistakes` remains supported.

Category percentage is that category's event count divided by all mistake events. Category recent frequency is its count in the latest configured attempt window divided by observed attempts in that window. Frequency trend compares rates in equal adjacent windows: `INCREASING`, `STABLE`, `DECREASING`, or `INSUFFICIENT_DATA`. Categories with zero events are omitted. The optional event timeline groups actual timestamps into daily or weekly buckets; fewer than the minimum mistakes or fewer than two observed buckets produces the message “Keep practicing to reveal your mistake patterns.” No missing calendar buckets are invented.

A repeated pattern groups events by the underlying error type, topic, subtopic, and actual correct/distractor answer pair. Where AMPA labels a later occurrence `REPEATED_MISTAKE`, the earlier same answer pair is used to associate it with its observed original category. A category with fewer than two occurrences is not listed. Trends require enough events and compare frequency per attempt span; otherwise they report insufficient data.

Concept confusion edges come from actual `CONCEPT_CONFUSION` answers and subsequent `REPEATED_MISTAKE` events with the same observed correct-answer/distractor pair. The response contains graph-ready `nodes` and `edges`, occurrence counts, recent counts, last occurrence, and trend. Edge `strength` is null because the existing model has no defined pair-strength or confidence metric; no confidence is fabricated. This works for concepts outside the initial configured examples when they are present in the actual choices.

## Recovery

For each mistake event with a complete following window of `W` attempts, recovery is successful if at least one of those attempts is correct. `recovery_count` is successful eligible mistake windows; `recovery_rate = recovery_count / eligible_mistakes`. `average_recovery_attempts` is the mean offset of the first correct attempt, counting from 1, among successful eligible windows. The API requires at least the configured minimum number of eligible windows before publishing a rate; otherwise the rate and average are null. Incomplete windows at the history tail are excluded.

## Configuration

- `MISTIQ_ANALYTICS_RECENT_WINDOW` (default `10` attempts)
- `MISTIQ_ANALYTICS_MINIMUM_SAMPLE` (default `3` per comparison window)
- `MISTIQ_ANALYTICS_TREND_THRESHOLD` (default `0.05`, an absolute rate difference)
- `MISTIQ_ANALYTICS_RECOVERY_WINDOW` (default `3` following attempts)
- `MISTIQ_ANALYTICS_MOMENTUM_MINIMUM` (default `10` attempts)
- `MISTIQ_ANALYTICS_MISTAKE_BUCKET` (`daily` or `weekly`, default `weekly`)

The UI uses a labeled line chart for accuracy and question difficulty, horizontal bars for topic/difficulty accuracy and mistake distribution, and a text relationship list for observed concept pairs. Sections without observations are omitted or show an explicit insufficient-data state. It uses one mistake summary API request for the common, repeated, confusion, timeline, and recent-event sections; the standalone list endpoints remain available to other clients.

## Limitations

Recorded response patterns are descriptive and are not psychological assessments or causal explanations. Difficulty trend coverage depends on which questions have been attempted. A recurring pair is inferred from answer text, so inconsistent wording can split equivalent concepts. Recovery describes any correct answer within the configured next-attempt window, not necessarily the same topic. AMPA stability and momentum retain their existing feature semantics and are not recalculated by this analytics phase.
