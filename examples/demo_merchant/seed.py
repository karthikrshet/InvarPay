"""
PayGuard AI — Demo Merchant Seed Module (python-package alias)
"""
import sys
import os
import importlib.util

# Load seed from demo-merchant
_current_dir = os.path.dirname(os.path.abspath(__file__))
_real_seed_path = os.path.join(os.path.dirname(_current_dir), "demo-merchant", "seed.py")

spec = importlib.util.spec_from_file_location("demo_merchant_seed_impl", _real_seed_path)
module = importlib.util.module_from_spec(spec)
sys.modules["demo_merchant_seed_impl"] = module
spec.loader.exec_module(module)

seed_demo_data = module.seed_demo_data

if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_demo_data())
