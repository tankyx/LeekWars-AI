#!/usr/bin/env python3
"""Cure-side boss-lobby joiner — runs on the home machine (Orange Pi 5 Plus)
so the join egresses from the home IP (LeekWars allows one WebSocket per IP;
the VPS holds main's squad open, this script joins cure into it).

Usage:
  python3 lw_cure_join.py <squad_id> [--hold-seconds N] [--leeks 1,2,3,4]

Behavior: logs in as the "cure" account from tools/config.json (same repo
layout as on the VPS), opens the boss WS, sends JOIN_SQUAD with the cure
leeks, prints JSON status lines to stdout, and HOLDS the connection until
the fight starts (member disconnect mid-lobby is untested — holding is the
safe default) or --hold-seconds elapses.

Exit codes: 0 joined (+ fight started), 2 join rejected/no such squad,
3 timeout, 4 auth/connection failure.
"""
import json
import os
import sys
import threading
import time

import requests
import websocket

BASE_URL = "https://leekwars.com/api"
WS_URL = "wss://leekwars.com/ws"

MSG = {"JOIN_SQUAD": 67, "LISTEN": 72, "SQUAD_JOINED": 74, "SQUAD": 76,
       "NO_SUCH_SQUAD": 77, "STARTED": 78, "LEFT": 82}


def out(obj):
    print(json.dumps(obj), flush=True)


def main():
    if len(sys.argv) < 2:
        out({"error": "usage: lw_cure_join.py <squad_id> [--hold-seconds N] [--leeks a,b,c,d]"})
        return 3
    squad_id = sys.argv[1]
    hold_seconds = 300
    leek_ids = None
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--hold-seconds" and i + 1 < len(args):
            hold_seconds = int(args[i + 1])
        if a == "--leeks" and i + 1 < len(args):
            leek_ids = [int(x) for x in args[i + 1].split(",")]

    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    cfg = json.load(open(cfg_path))["accounts"]["cure"]

    s = requests.Session()
    r = s.post(f"{BASE_URL}/farmer/login-token",
               data={"login": cfg["email"], "password": cfg["password"]}, timeout=15)
    data = r.json()
    if "token" not in data:
        out({"error": f"cure login failed: {str(data)[:200]}"})
        return 4
    farmer = data.get("farmer") or {}
    if leek_ids is None:
        leeks = farmer.get("leeks") or {}
        leek_ids = [int(k) for k in leeks.keys()] if isinstance(leeks, dict) else [int(l["id"]) for l in leeks]
    # follow-up GET so __Host-sess is set for WS auth
    s.get(f"{BASE_URL}/farmer/get", timeout=15)
    cookies = "; ".join(f"{k}={v}" for k, v in s.cookies.items())

    state = {"joined": False, "started": None, "no_such": False, "closed": False}

    def on_message(ws, message):
        try:
            msg = json.loads(message)
        except Exception:
            return
        if not isinstance(msg, list) or not msg:
            return
        mtype = msg[0]
        if mtype in (MSG["SQUAD_JOINED"], MSG["SQUAD"]):
            if len(msg) > 1 and isinstance(msg[1], dict) and msg[1].get("id") == squad_id:
                if not state["joined"]:
                    state["joined"] = True
                    out({"status": "joined", "squad": squad_id,
                         "farmers": len(msg[1].get("farmers") or []),
                         "engaged": msg[1].get("engaged_count")})
        elif mtype == MSG["STARTED"] and len(msg) > 1:
            state["started"] = msg[1]
            out({"status": "started", "fight_id": msg[1],
                 "url": f"https://leekwars.com/fight/{msg[1]}"})
        elif mtype == MSG["NO_SUCH_SQUAD"]:
            state["no_such"] = True
            out({"status": "no_such_squad", "squad": squad_id})
        elif mtype == MSG["LEFT"]:
            state["closed"] = True

    def on_error(ws, e):
        out({"status": "ws_error", "error": str(e)[:200]})

    ws = websocket.WebSocketApp(
        WS_URL,
        header={"Cookie": cookies},
        on_message=on_message,
        on_error=on_error,
        on_close=lambda ws, c, m: out({"status": "closed", "code": c}),
    )
    t = threading.Thread(target=ws.run_forever, daemon=True)
    t.start()
    time.sleep(1.5)
    ws.send(json.dumps([MSG["LISTEN"], 0]))
    time.sleep(0.3)
    ws.send(json.dumps([MSG["JOIN_SQUAD"], squad_id, leek_ids]))

    t0 = time.time()
    while time.time() - t0 < hold_seconds:
        if state["started"] is not None:
            time.sleep(1)
            try:
                ws.close()
            except Exception:
                pass
            return 0
        if state["no_such"]:
            try:
                ws.close()
            except Exception:
                pass
            return 2
        time.sleep(0.5)

    out({"status": "timeout", "joined": state["joined"], "squad": squad_id})
    try:
        ws.close()
    except Exception:
        pass
    return 3 if state["joined"] else 4


if __name__ == "__main__":
    sys.exit(main())
