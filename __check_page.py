import urllib.request

req = urllib.request.Request("http://localhost:3000")
resp = urllib.request.urlopen(req, timeout=10)
html = resp.read().decode("utf-8")
print(f"HTML length: {len(html)}")
has_next = "__next" in html
has_script = "<script" in html
print(f"Has __next: {has_next}")
print(f"Has scripts: {has_script}")
# Show first and last portions
print("---FIRST 800---")
print(html[:800])
print("---LAST 800---")
print(html[-800:])
