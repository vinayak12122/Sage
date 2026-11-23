from huggingface_hub import HfApi

api = HfApi()
api.create_repo("vinnu01/tinyllm-v1",repo_type='model' ,exist_ok=True)
api.upload_file(
    path_or_fileobj="llm/weights/tinyllm_v5_fp16_weights.pt",
    path_in_repo="tinyllm_v5_fp16_weights.pt",
    repo_id="vinnu01/tinyllm-v1",
    repo_type="model"
)