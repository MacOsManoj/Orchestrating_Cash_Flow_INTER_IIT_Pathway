"""
vLLM server on Modal - runs continuously.
Deploy once with: modal deploy vllm_server.py
"""

import modal
import subprocess

app = modal.App("sebi-vllm-server")

# Model configuration
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REVISION = None  # Use latest version

# Create Modal image with vLLM
vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install(
        "vllm==0.11.2",
        "huggingface-hub==0.36.0",
    )
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

# Modal Volumes for caching
hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)

# Configuration
N_GPU = 1
MINUTES = 60
VLLM_PORT = 8000
FAST_BOOT = True  # Set to False for better performance


@app.function(
    image=vllm_image,
    gpu=f"A10G:{N_GPU}",
    scaledown_window=60 * MINUTES,  # Keep running for 1 hour after last request
    timeout=120 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve():
    """Serve vLLM in OpenAI-compatible mode."""
    cmd = [
        "vllm",
        "serve",
        "--uvicorn-log-level=info",
        MODEL_NAME,
        "--served-model-name",
        "llm",
        "--host",
        "0.0.0.0",
        "--port",
        str(VLLM_PORT),
    ]

    # Add revision if specified
    if MODEL_REVISION:
        cmd.extend(["--revision", MODEL_REVISION])

    cmd += ["--enforce-eager" if FAST_BOOT else "--no-enforce-eager"]
    cmd += ["--tensor-parallel-size", str(N_GPU)]

    print("Starting vLLM server with command:", " ".join(cmd))
    subprocess.Popen(" ".join(cmd), shell=True)


@app.local_entrypoint()
def main():
    """Get the vLLM server URL."""
    url = serve.web_url
    print(f"\n🚀 vLLM Server URL: {url}")
    print(f"\n📝 Save this URL to use in your local processing script!")
    print(f"\nServer will stay running for 60 minutes after last request.")
    print(f"\nTo stop: modal app stop sebi-vllm-server")
