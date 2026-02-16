from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth_headers(tid: int = 12345):
    r = client.post('/api/v1/auth/telegram', json={'telegram_id': tid})
    token = r.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_profile_flow():
    headers = _auth_headers()
    r = client.get('/api/v1/profile/me', headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body['level'] == 1
    assert body['hp_max'] == 100


def test_combat_start_and_attack():
    headers = _auth_headers(999)
    start = client.post('/api/v1/combat/pve/start', json={'mob_level': 1}, headers=headers)
    assert start.status_code == 200
    combat_id = start.json()['combat_id']

    attack = client.post(f'/api/v1/combat/{combat_id}/turn/attack', json={'zone': 'mid'}, headers=headers)
    assert attack.status_code == 200
    assert attack.json()['enemy_hp'] < start.json()['enemy_hp']
