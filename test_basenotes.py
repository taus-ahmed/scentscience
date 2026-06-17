import requests
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
r = requests.get('https://www.basenotes.net/fragrances/', headers=headers, timeout=10)
print(r.status_code, len(r.text))
print(r.text[:500])
