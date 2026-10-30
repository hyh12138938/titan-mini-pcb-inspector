import urllib.request, base64, os
url = "https://cacerts.digicert.com/DigiCertGlobalRootG2.crt"
der = urllib.request.urlopen(url, timeout=20).read()
print("downloaded bytes", len(der))
b64 = base64.encodebytes(der).decode("ascii")
pem = "-----BEGIN CERTIFICATE-----\r\n" + b64.replace("\n", "\r\n").strip() + "\r\n-----END CERTIFICATE-----\r\n"
dst = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_driver_eth\packages\mbedtls-latest\certs\user\DIGICERT_GLOBAL_ROOT_G2.cer"
os.makedirs(os.path.dirname(dst), exist_ok=True)
open(dst, "w", newline="").write(pem)
print("written", dst)
print(pem[:80])
