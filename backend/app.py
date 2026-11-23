try:
    import spaces
    @spaces.GPU
    def _placeholder():
        return "ok"
except ImportError:
    pass

import os
import uvicorn
from huggingface_hub import hf_hub_download

WEIGHTS_REPO = os.getenv("WEIGHTS_REPO", "vinnu01/tinyllm-v1")
WEIGHTS_FILE = "tinyllm_v5_fp16_weights.pt"

os.makedirs("llm/weights", exist_ok=True)
hf_hub_download(repo_id=WEIGHTS_REPO, filename=WEIGHTS_FILE, local_dir="llm/weights")
os.environ.setdefault("MODEL_WEIGHTS_PATH", f"llm/weights/{WEIGHTS_FILE}")


import torch
from llm import config 

config.DEVICE = torch.device("cpu")

from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)