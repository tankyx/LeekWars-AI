// Four-leaf clover catcher (owner 2026-11-05). The server pushes LUCKY (26) on the site's WebSocket to the
// farmers connected when today's clover passes; the web client shows it for 5 s and a click sends GET_LUCKY (27)
// (leek-wars/leek-wars src/model/socket.ts, src/component/app/app.vue). FAKE_LUCKY (61) is the runaway decoy.
// Trophies: lucky (1 clover, 90k habs), attentive (2 clovers, 250k habs).
//
//   node tools/clover_watch.mjs                       # every account in tools/config.json, forever
//   node tools/clover_watch.mjs --accts main,cure
// Detached: setsid nohup node tools/clover_watch.mjs >> /tmp/clover_watch.log 2>&1 &
// Catches: data/ladder/clover.log. One socket per account, PING (90) every 50 s like the site, reconnect +
// re-login with backoff on any close.
import { createRequire } from 'module'
import { readFileSync, appendFileSync } from 'fs'
const require = createRequire('/home/ubuntu/claude-code/mcp-leekwars-server/package.json')
const WebSocket = require('ws')

const API = 'https://leekwars.com/api'
const WS = 'wss://leekwars.com/ws'
const MSG = { LUCKY: 26, GET_LUCKY: 27, WRONG_TOKEN: 57, FAKE_LUCKY: 61, PING: 90 }
const argv = process.argv.slice(2)
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d }
const cfg = JSON.parse(readFileSync(new URL('./config.json', import.meta.url), 'utf-8')).accounts
const ACCTS = opt('--accts', Object.keys(cfg).join(',')).split(',').filter(Boolean)
const CATCH_LOG = new URL('../data/ladder/clover.log', import.meta.url)
const ts = () => new Date().toISOString().replace('T', ' ').slice(0, 19)
const log = (s) => console.log(ts() + ' ' + s)
const wait = (ms) => new Promise(r => setTimeout(r, ms))

async function login(acct) {
  const a = cfg[acct]
  const r = await fetch(API + '/farmer/login-token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'login=' + encodeURIComponent(a.email) + '&password=' + encodeURIComponent(a.password) })
  const j = await r.json()
  if (!j.token) throw new Error('login failed for ' + acct)
  return j.token
}

async function watch(acct) {
  let delay = 2000
  for (;;) {
    let token
    try { token = await login(acct) } catch (e) { log(acct + ': ' + e.message + ' - retry in ' + delay / 1000 + ' s'); await wait(delay); delay = Math.min(delay * 2, 300000); continue }
    await new Promise((done) => {
      const ws = new WebSocket(WS, ['leek-wars', token], { headers: { Origin: 'https://leekwars.com' },
        finishRequest: (req) => { req.setHeader('Sec-WebSocket-Protocol', 'leek-wars, ' + token); req.end() } })
      let ping = null
      ws.on('open', () => {
        delay = 2000
        log(acct + ': connected')
        ping = setInterval(() => { if (ws.readyState === 1) ws.send(JSON.stringify([MSG.PING])) }, 50000)
      })
      ws.on('message', (m) => {
        let msg; try { msg = JSON.parse(String(m)) } catch { return }
        if (msg[0] === MSG.LUCKY) {
          ws.send(JSON.stringify([MSG.GET_LUCKY]))
          log(acct + ': CLOVER - GET_LUCKY sent')
          try { appendFileSync(CATCH_LOG, ts() + ' ' + acct + ' clover caught\n') } catch {}
        } else if (msg[0] === MSG.FAKE_LUCKY) {
          log(acct + ': fake clover (decoy) ignored')
        } else if (msg[0] === MSG.WRONG_TOKEN) {
          log(acct + ': wrong token - re-login'); ws.close()
        }
      })
      ws.on('error', (e) => log(acct + ': socket error ' + (e && e.message)))
      ws.on('close', (code) => { if (ping) clearInterval(ping); log(acct + ': closed (' + code + ')'); done() })
    })
    await wait(delay); delay = Math.min(delay * 2, 300000)
  }
}

log('clover watch: ' + ACCTS.join(', '))
await Promise.all(ACCTS.map(watch))
