// Browser-level Phase 6 flow using Edge/Chrome's DevTools Protocol (no Playwright dependency).
const targets = await (await fetch('http://127.0.0.1:9222/json')).json()
const target = targets.find(item => item.type === 'page' && item.url.startsWith('http://127.0.0.1:5173'))
if (!target) throw new Error('Open the MISTIQ frontend in the headless browser first.')

const socket = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true })
  socket.addEventListener('error', reject, { once: true })
})
let nextId = 0
const pending = new Map()
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data)
  if (!message.id) return
  const callbacks = pending.get(message.id)
  if (!callbacks) return
  pending.delete(message.id)
  if (message.error) callbacks.reject(new Error(message.error.message))
  else callbacks.resolve(message.result)
})

function send(method, params = {}) {
  const id = ++nextId
  socket.send(JSON.stringify({ id, method, params }))
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }))
}
async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text)
  return result.result.value
}
async function waitFor(expression, timeout = 10000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    const value = await evaluate(expression)
    if (value) return value
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  throw new Error(`Timed out waiting for: ${expression}`)
}
async function fill(inputSelector, value) {
  return evaluate(`(() => { const input = document.querySelector(${JSON.stringify(inputSelector)}); const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; setter.call(input, ${JSON.stringify(value)}); input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); return true })()`)
}
async function screenshot(path) {
  const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
  const { writeFile } = await import('node:fs/promises')
  await writeFile(path, Buffer.from(data, 'base64'))
}

await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true })
await send('Page.navigate', { url: 'http://127.0.0.1:5173/login' })
await waitFor("document.readyState === 'complete'")
await evaluate('localStorage.clear(); location.reload(); true')
await waitFor("!!document.querySelector('#student-name')")
await fill('#student-name', 'Phase 6 browser learner')
await evaluate("document.querySelector('.entry-card form button[type=submit]').click()")
let dashboardHeading
try { dashboardHeading = await waitFor("document.querySelector('.page-header h1')?.innerText.includes('Good to see you')") }
catch { throw new Error(`Development entry did not reach dashboard: ${await evaluate('document.body.innerText')}`) }
const studentId = await evaluate("Number(localStorage.getItem('mistiq.development.studentId'))")
await screenshot('.test-output/phase6-dashboard-mobile.png')

await evaluate("document.querySelector('a[href=\"/practice\"]').click()")
const questionText = await waitFor("document.querySelector('.question-card h2')?.innerText")
await screenshot('.test-output/phase6-practice-mobile.png')
// Question 1 in the development SQLite database designates A as correct; select B for real mistake feedback.
await evaluate("document.querySelector('input[type=radio][value=B]').click()")
await evaluate("document.querySelector('.question-actions button').click()")
const feedback = await waitFor("document.querySelector('.feedback-panel h3')?.innerText")
if (feedback !== 'Not quite.') throw new Error(`Expected incorrect-answer feedback, got: ${feedback}`)
const attemptSummary = await evaluate(`fetch('/api/students/${studentId}/progress').then(response => response.json())`)
if (attemptSummary.attempt_count < 1 || attemptSummary.mistake_count < 1) throw new Error('Backend progress/mistake state did not update after the browser attempt.')
await screenshot('.test-output/phase6-feedback-mobile.png')
await evaluate("document.querySelector('a[href=\"/progress\"]').click()")
await waitFor("document.querySelector('.page-header h1')?.innerText === 'Your progress'")
const progressVisible = await evaluate("document.body.innerText.includes('1') && document.body.innerText.includes('0%')")
if (!progressVisible) throw new Error('Progress page did not show the submitted interaction.')
await evaluate("document.querySelector('a[href=\"/mistakes\"]').click()")
await waitFor("document.body.innerText.includes('Patterns to learn from')")
const mistakesVisible = await evaluate("document.body.innerText.includes('Concept confusion')")
if (!mistakesVisible) throw new Error('Mistakes page did not show the backend-created mistake.')

const viewportChecks = []
for (const width of [320, 390, 768, 1024, 1440]) {
  await send('Emulation.setDeviceMetricsOverride', { width, height: width < 761 ? 844 : 900, deviceScaleFactor: 1, mobile: width < 761 })
  const dimensions = await evaluate('({ viewport: window.innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth })')
  if (dimensions.document > dimensions.viewport || dimensions.body > dimensions.viewport) throw new Error(`Horizontal overflow at ${width}px: ${JSON.stringify(dimensions)}`)
  viewportChecks.push(width)
  if (width === 1440) await screenshot('.test-output/phase6-mistakes-desktop.png')
}
console.log(JSON.stringify({ studentId, questionText, feedback, progress: attemptSummary, progressVisible, mistakesVisible, viewportWidthsChecked: viewportChecks, horizontalOverflow: false }, null, 2))
socket.close()
