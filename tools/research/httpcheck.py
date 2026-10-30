import urllib.request
for url in ("http://192.168.137.1:8000/img_test_320x240.jpg", "http://127.0.0.1:8000/img_test_320x240.jpg"):
    try:
        d = urllib.request.urlopen(url, timeout=5).read()
        print("OK  %-45s %d bytes" % (url, len(d)))
    except Exception as e:
        print("ERR %-45s %s" % (url, e))
