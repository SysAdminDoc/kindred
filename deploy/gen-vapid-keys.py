"""
Generate VAPID keys for web push notifications.
Run once, then paste the output into your .env file.
"""

try:
    from py_vapid import Vapid
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-vapid"])
    from py_vapid import Vapid

import base64

vapid = Vapid()
vapid.generate_keys()

raw_priv = vapid.private_key.private_numbers().private_value
priv_bytes = raw_priv.to_bytes(32, byteorder="big")
private_key = base64.urlsafe_b64encode(priv_bytes).decode().rstrip("=")

raw_pub = vapid.public_key.public_bytes(
    encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.X962,
    format=__import__("cryptography").hazmat.primitives.serialization.PublicFormat.UncompressedPoint,
)
public_key = base64.urlsafe_b64encode(raw_pub).decode().rstrip("=")

print()
print("Add these to your .env file:")
print()
print(f"KINDRED_VAPID_PUBLIC_KEY={public_key}")
print(f"KINDRED_VAPID_PRIVATE_KEY={private_key}")
print(f"KINDRED_VAPID_CONTACT=mailto:you@yourdomain.com")
print()
