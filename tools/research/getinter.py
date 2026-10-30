import urllib.request, base64
url = "http://cacerts.digicert.com/TrustAsiaDVTLSRSACA2025.crt"
try:
    der = urllib.request.urlopen(url, timeout=20).read()
    print("intermediate bytes", len(der))
    open(r"D:\RTT\_tmp\inter.der","wb").write(der)
except Exception as e:
    print("ERR", e)
