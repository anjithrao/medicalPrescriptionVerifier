from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="Anji-th/prescription-trocr",
    local_dir="trocr_best"
)

print("Model downloaded successfully.")