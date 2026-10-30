import inspect
from ethosu.vela import api
names = [n for n in dir(api) if not n.startswith('_')]
print("api:", names)
for n in ("optimise_model","npu_performance_estimate","read_model"):
    if hasattr(api, n):
        print(n, inspect.signature(getattr(api, n)))
