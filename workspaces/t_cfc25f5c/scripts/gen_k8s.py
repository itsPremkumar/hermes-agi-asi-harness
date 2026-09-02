"""Generate default Kubernetes manifests for ContextVault."""

from contextvault.k8s_operator import generate_default_manifests
import os

output_dir = "k8s"
os.makedirs(output_dir, exist_ok=True)
files = generate_default_manifests(output_dir)
print(f"Generated {len(files)} manifests:")
for f in files:
    print(f"  {f}")
