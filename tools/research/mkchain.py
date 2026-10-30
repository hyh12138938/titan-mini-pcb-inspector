import base64, os
def der2pem(der):
    b = base64.encodebytes(der).decode("ascii").strip()
    return "-----BEGIN CERTIFICATE-----\r\n" + b.replace("\n", "\r\n") + "\r\n-----END CERTIFICATE-----\r\n"
user = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_driver_eth\packages\mbedtls-latest\certs\user"
root_pem = open(os.path.join(user, "DIGICERT_GLOBAL_ROOT_G2.cer"), "r").read()
inter_pem = der2pem(open(r"D:\RTT\_tmp\inter.der", "rb").read())
# remove old single files, write one bundle: intermediate + root
for f in os.listdir(user):
    os.remove(os.path.join(user, f))
open(os.path.join(user, "TRUSTASIA_CHAIN.cer"), "w", newline="").write(inter_pem + root_pem)
print("bundle bytes", len(inter_pem + root_pem))
