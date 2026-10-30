import ssl, socket
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
with socket.create_connection(("api.deepseek.com", 443), timeout=10) as s:
    with ctx.wrap_socket(s, server_hostname="api.deepseek.com") as ss:
        der = ss.getpeercert(binary_form=True)
open(r"D:\RTT\_tmp\leaf.cer", "wb").write(der)
print("leaf bytes", len(der))
