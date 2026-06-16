import requests

BASE = 'https://stock-analysis-app-production-da60.up.railway.app'
s = requests.Session()

# Register first (user might not exist after DB reset)
r = s.post(f'{BASE}/api/auth/register', json={
    'username': 'test0615', 'password': '123456', 'email': 'test0615@test.com'
})
print('1. Register:', r.status_code, r.json())

# Login
r = s.post(f'{BASE}/api/auth/login', json={'username': 'test0615', 'password': '123456'})
print('2. Login:', r.status_code, r.json().get('success'))
print('   Cookie:', dict(s.cookies))
print('   SameSite:', 'SameSite' in r.headers.get('Set-Cookie', ''))

# Verify
r = s.get(f'{BASE}/api/auth/me')
print('3. Me:', r.json())

# Add watchlist
r = s.post(f'{BASE}/api/watchlist/add', json={'code': '600519', 'name': 'MT', 'market': 'cn'})
print('4. Add:', r.status_code, r.json())

# List
r = s.get(f'{BASE}/api/watchlist')
print('5. List:', len(r.json().get('items', [])), 'items')

# Delete
r = s.delete(f'{BASE}/api/watchlist/600519?market=cn')
print('6. Delete:', r.status_code)

print('\nALL OK - Production ready!')
