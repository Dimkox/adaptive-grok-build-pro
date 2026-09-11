import os
import urllib.error
import urllib.request

os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

req = urllib.request.Request(
    "http://127.0.0.1/",
    headers={"Host": "trust-ci.ii-tonya.ru"},
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("HTTP", resp.status)
except urllib.error.HTTPError as exc:
    print("HTTP", exc.code, exc.reason)
