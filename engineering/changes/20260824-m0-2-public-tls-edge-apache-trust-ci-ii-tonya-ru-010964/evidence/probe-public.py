import os
import ssl
import urllib.error
import urllib.request

os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"


def probe(url: str, method: str = "GET", headers: dict | None = None, data: bytes | None = None, verify: bool = True) -> None:
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            body = resp.read(200).decode("utf-8", "replace")
            print(url, "HTTP", resp.status, body.replace("\n", " ")[:160])
    except urllib.error.HTTPError as exc:
        body = exc.read(200).decode("utf-8", "replace")
        print(url, "HTTP", exc.code, exc.reason, body.replace("\n", " ")[:160])
    except Exception as exc:
        print(url, "ERR", type(exc).__name__, exc)


probe("https://trust-ci.ii-tonya.ru/health/ready")
probe("https://trust-ci.ii-tonya.ru/health/ready", verify=False)
probe("http://trust-ci.ii-tonya.ru/health/ready")
probe(
    "https://trust-ci.ii-tonya.ru/webhooks/github",
    method="POST",
    headers={"Content-Type": "application/json", "X-GitHub-Event": "ping"},
    data=b"{}",
    verify=False,
)
probe("https://ii-tonya.ru/health/ready")
probe(
    "https://ii-tonya.ru/webhooks/github",
    method="POST",
    headers={"Content-Type": "application/json", "X-GitHub-Event": "ping"},
    data=b"{}",
)
probe("https://ii-tonya.ru/")

import socket

def cert_names(host: str) -> None:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, 443), timeout=12) as raw:
        with ctx.wrap_socket(raw, server_hostname=host) as sock:
            cert = sock.getpeercert()
            print("CERT", host, "subject", cert.get("subject"), "SAN", cert.get("subjectAltName"))

try:
    cert_names("trust-ci.ii-tonya.ru")
except Exception as exc:
    print("CERT trust-ci ERR", type(exc).__name__, exc)
try:
    cert_names("ii-tonya.ru")
except Exception as exc:
    print("CERT apex ERR", type(exc).__name__, exc)
