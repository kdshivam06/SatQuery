# Serverless Inference Layer for Custom SAR-Optical Model

Provider-neutral on-demand serverless worker package for the SatQuery custom SAR↔Optical model.

## Features
- **Provider-Neutral Entrypoint**: `handle_inference(event, context)` function suitable for wrapping in AWS Lambda, Modal, RunPod, Replicate, or Docker containers.
- **Process-Level Warm Caching**: Models are lazy-loaded once and reused across warm invocations without reloading checkpoint weights per request.
- **Preprocessing Parity**: Reuses exact `prepare_bigearthnet_input` and band-mapping routines from `backend.modeling`.
- **Structured JSON Response**: Returns similarity, matched status, agreement confidence, and predicted labels.

## Usage

```python
from serverless.custom_sar_optical.handler import handle_inference

response = handle_inference({
    "sar_input_path": "/path/to/sar_stack.npy",
    "optical_input_path": "/path/to/optical_stack.npy"
})
print(response)
```
