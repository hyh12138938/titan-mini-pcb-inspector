import ssl, socket
ctx = ssl.create_default_context()
with socket.create_connection(("api.deepseek.com", 443), timeout=10) as s:
    with ctx.wrap_socket(s, server_hostname="api.deepseek.com") as ss:
        c = ss.getpeercert()
for k in ("subject", "issuer"):
    print(k, "=", c.get(k))
print("notAfter =", c.get("notAfter"))
print("SAN =", c.get("subjectAltName"))
