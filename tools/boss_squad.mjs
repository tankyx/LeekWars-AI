// Cross-account boss squads: main's 4 leeks + Cure's 4 leeks in one boss fight (Fennel / Pumpkin).
//
//   node tools/boss_squad.mjs --boss 3 --n 10          # 10 eight-leek Pumpkin fights
//   node tools/boss_squad.mjs --boss 2 --n 1 --dry     # form the squad, print it, leave (no fight)
//
// Flow per fight (WebSocket, as the web client does): main creates a locked squad with its leeks,
// Cure joins with its leeks, main sends ATTACK; the squad dissolves on attack, so it is re-formed for
// every fight. The REST route garden/start-boss-fight-batch only took the master's leeks (2026-10-19),
// so fights go through the socket. Each farmer with engaged leeks pays 1 credit per fight: Cure's
// leeks are only engaged while Cure has credits.
//
// Auth: Sec-WebSocket-Protocol "leek-wars, <token>" with the browser's ", " separator (Node's ws joins
// with "," -> HTTP 404), set in finishRequest. The first socket after a login often closes at once
// (1006): reconnect. Prints "started <fight id>" lines (boss_v10_batch.py --ids reads them).
import { createRequire } from 'module'
import { readFileSync } from 'fs'
const require = createRequire('/home/ubuntu/claude-code/mcp-leekwars-server/package.json')
const WebSocket = require('ws')

const API = 'https://leekwars.com/api'
const WS = 'wss://leekwars.com/ws'
const MSG = { CREATE: 66, JOIN: 67, ATTACK: 71, LISTEN: 72, SQUADS: 73, JOINED: 74, LEAVE: 75, SQUAD: 76, NO_SUCH: 77, STARTED: 78, LEFT: 82 }
const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const BOSS = parseInt(opt('--boss', '3')), N = parseInt(opt('--n', '1')), DRY = argv.includes('--dry')
const cfg = JSON.parse(readFileSync(new URL('./config.json', import.meta.url), 'utf-8')).accounts
const t0 = Date.now()
const log = (s) => console.log(((Date.now() - t0) / 1000).toFixed(1).padStart(6) + 's ' + s)
const wait = (ms) => new Promise(r => setTimeout(r, ms))

async function login(acct) {
  const a = cfg[acct]
  const r = await fetch(API + '/farmer/login-token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'login=' + encodeURIComponent(a.email) + '&password=' + encodeURIComponent(a.password) })
  const j = await r.json()
  if (!j.token) throw new Error('login failed for ' + acct)
  return { name: acct, token: j.token, farmer: j.farmer.id, leeks: Object.values(j.farmer.leeks).map(l => l.id), squad: null, started: null, ws: null }
}

function connect(acc) {
  return new Promise((res) => {
    const ws = new WebSocket(WS, ['leek-wars', acc.token], { headers: { Origin: 'https://leekwars.com' },
      finishRequest: (req) => { req.setHeader('Sec-WebSocket-Protocol', 'leek-wars, ' + acc.token); req.end() } })
    ws.on('open', () => { ws.send(JSON.stringify([MSG.LISTEN])); res(ws) })
    ws.on('error', () => res(ws))
    ws.on('message', (m) => {
      let msg; try { msg = JSON.parse(String(m)) } catch { return }
      if (msg[0] === MSG.JOINED || msg[0] === MSG.SQUAD) acc.squad = msg[1]
      else if (msg[0] === MSG.STARTED) acc.started = msg[1]
      else if (msg[0] === MSG.NO_SUCH || msg[0] === MSG.LEFT) acc.squad = null
    })
  })
}

async function socket(acc) {
  for (let k = 0; k < 5; k++) {
    if (acc.ws && acc.ws.readyState === 1) return true
    acc.ws = await connect(acc)
    await wait(1500)
  }
  return acc.ws.readyState === 1
}

async function until(f, ms) {
  for (let t = 0; t < ms; t += 200) { if (f()) return true; await wait(200) }
  return !!f()
}

const send = (acc, m) => acc.ws.send(JSON.stringify(m))
const engaged = (acc) => (acc.squad && acc.squad.engaged_leeks || []).length

const main = await login('main'), cure = await login('cure')
const want = main.leeks.length + cure.leeks.length
log(`boss ${BOSS}: main ${main.leeks.length} leeks + cure ${cure.leeks.length} leeks, ${DRY ? 'dry run' : N + ' fights'}`)
const ids = []
for (let i = 0; i < N; i++) {
  if (!await socket(main) || !await socket(cure)) { log('cannot hold both sockets - stop'); break }
  main.squad = cure.squad = null; main.started = cure.started = null
  send(main, [MSG.CREATE, BOSS, true, main.leeks])
  if (!await until(() => main.squad, 8000)) { log('squad not created (main out of credits?) - stop'); break }
  send(cure, [MSG.JOIN, main.squad.id, cure.leeks])
  if (!await until(() => engaged(main) >= want, 8000)) {
    log(`only ${engaged(main)}/${want} leeks engaged (cure out of credits?) - leaving, stop`)
    send(cure, [MSG.LEAVE]); send(main, [MSG.LEAVE]); await wait(800); break
  }
  if (DRY) {
    log('squad ' + main.squad.id + ': ' + main.squad.engaged_leeks.map(l => l.name + '(' + l.level + ')').join(' '))
    send(cure, [MSG.LEAVE]); send(main, [MSG.LEAVE]); await wait(800); break
  }
  send(main, [MSG.ATTACK])
  if (!await until(() => main.started || cure.started, 15000)) { log('attack not started - leaving, stop'); send(cure, [MSG.LEAVE]); send(main, [MSG.LEAVE]); await wait(800); break }
  const fid = (main.started || cure.started)[0]
  ids.push(fid)
  console.log('started ' + fid + ' (' + (i + 1) + '/' + N + ')')
  await wait(1000)
}
log('fights ' + JSON.stringify(ids))
for (const a of [main, cure]) { try { a.ws.close() } catch { } }
setTimeout(() => process.exit(0), 300)
