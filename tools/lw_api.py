#!/usr/bin/env python3
"""Resilient LeekWars API client shared by the tooling.

leekwars.com will drop a connection or read-timeout during any long run, and an
unhandled one loses whatever the script had accumulated. Every call here retries
network faults AND the 5-req/sec rate limiter with backoff.

    from lw_api import LWSession
    lw = LWSession('main')            # logs in, holds the bearer token
    farmer = lw.farmer                # login payload's farmer object
    d = lw.post('/item/recycle', item_id=123)
    d = lw.get('/leek/get/20443')
"""
import time

import requests

from config_loader import load_credentials

BASE = 'https://leekwars.com/api'


class LWSession:
    def __init__(self, account='main', timeout=25, retries=8):
        self.timeout, self.retries = timeout, retries
        email, pw = load_credentials(account)
        self.s = requests.Session()
        j = self.s.post(f'{BASE}/farmer/login-token',
                        data={'login': email, 'password': pw}, timeout=timeout).json()
        if 'farmer' not in j:
            raise RuntimeError(f'login failed for {account}: {str(j)[:200]}')
        self.farmer = j['farmer']
        self.token = j['token']
        self.s.headers['Authorization'] = 'Bearer ' + self.token

    def call(self, method, path, **data):
        d = {'error': 'not_attempted'}
        for attempt in range(self.retries):
            try:
                r = self.s.request(method, f'{BASE}{path}',
                                   data=data if method != 'GET' else None,
                                   params=data if method == 'GET' else None,
                                   timeout=self.timeout)
                try:
                    d = r.json()
                except ValueError:
                    d = {'error': 'bad_json', 'body': r.text[:200]}
            except requests.exceptions.RequestException as ex:
                time.sleep(min(2 ** attempt, 20))
                d = {'error': 'network', 'detail': type(ex).__name__}
                continue
            if isinstance(d, dict) and d.get('error') == 'rate_limit':
                time.sleep(float(d.get('retry_after', 1)) + 0.3)
                continue
            return d
        return d

    def get(self, path, **data):
        return self.call('GET', path, **data)

    def post(self, path, **data):
        return self.call('POST', path, **data)

    def leek(self, leek_id):
        d = self.get(f'/leek/get/{leek_id}')
        return d.get('leek', d) if isinstance(d, dict) else {}
