from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from . import config
from .domain import cents

COLLECTIONS = {'items': 'listings', 'quotes': 'quotes', 'orders': 'orders', 'policies': 'policies', 'exceptions': 'cases', 'audit': 'audit_events'}


def connect():
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row)


def seed():
    return json.loads(Path(__file__).with_name('seed.json').read_text(encoding='utf-8'))


def setup():
    with connect() as conn:
        # One startup migration/seed writer even with multiple API processes.
        conn.execute('SELECT pg_advisory_xact_lock(5620001)')
        conn.execute((config.ROOT / 'migrations/001_initial.sql').read_text(encoding='utf-8'))
        if not conn.execute('SELECT 1 FROM app_meta WHERE id=1').fetchone():
            conn.execute('INSERT INTO app_meta VALUES (1,%s)', (Jsonb({}),))
            save(conn, seed())


def read(conn, lock=False):
    row = conn.execute('SELECT payload FROM app_meta WHERE id=1' + (' FOR UPDATE' if lock else '')).fetchone()
    s = deepcopy(row['payload'])
    ordering = s.pop('_ordering', {})
    for key, table in COLLECTIONS.items():
        values = {r['id']: r['payload'] for r in conn.execute(f'SELECT id,payload FROM {table}').fetchall()}
        s[key] = [values[k] for k in ordering.get(key, values.keys()) if k in values]
    return s


def snapshot():
    with connect() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        return read(conn)


def save(conn, s):
    meta = {k: v for k, v in s.items() if k not in COLLECTIONS}
    meta['_ordering'] = {}
    for key, table in COLLECTIONS.items():
        rows = s[key]
        identifiers = [f"{r['id']}:{r['version']}" if key == 'policies' else r['id'] for r in rows]
        meta['_ordering'][key] = identifiers
        if identifiers:
            conn.execute(f'DELETE FROM {table} WHERE NOT (id = ANY(%s))', (identifiers,))
        else:
            conn.execute(f'DELETE FROM {table}')
        for identifier, row in zip(identifiers, rows):
            conn.execute(f'INSERT INTO {table}(id,payload) VALUES (%s,%s) ON CONFLICT(id) DO UPDATE SET payload=EXCLUDED.payload', (identifier, Jsonb(row)))
    conn.execute('UPDATE app_meta SET payload=%s WHERE id=1', (Jsonb(meta),))
    for order in s['orders']:
        conn.execute('INSERT INTO payments VALUES (%s,%s,%s,%s) ON CONFLICT(order_id) DO NOTHING',
                     (order['paymentKey'], order['id'], cents(order['total']), order.get('method', 'Demo seed')))
        if order['status'] == 'settled':
            seller = cents(order['item']['price']) - cents(Decimal(str(order['item']['price'])) * Decimal('.02'))
            carrier = cents(order['deliveryFee']) - cents(Decimal(str(order['deliveryFee'])) * Decimal('.1'))
            conn.execute('INSERT INTO settlements VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(order_id) DO NOTHING',
                         (order['payoutKey'], order['id'], seller, carrier, cents(order['total']) - seller - carrier, order['settledAt']))


@contextmanager
def transaction():
    with connect() as conn:
        state = read(conn, lock=True)
        yield conn, state
        save(conn, state)
