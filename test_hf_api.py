"""Test the remote LLM router via HF Inference API."""
import sys, os, json, time
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv("backend/.env", override=True)

from backend.agent.router_llm import _llm_route

test_input = {
    "query": "Detect water bodies and estimate area",
    "input_summary": {
        "configuration": "single",
        "modalities": ["multispectral"],
        "available_bands": {"multispectral": ["B02","B03","B04","B08","B11","B12"]},
    },
    "available_tools": [
        "metadata_reader", "preview_generator",
        "ndvi_vegetation_detector", "ndwi_water_detector", "mndwi_water_detector",
        "ndbi_builtup_detector", "area_calculator", "overlay_generator",
        "rsllava_vqa_caption_tool", "custom_sar_optical_dual_encoder_tool",
    ],
}

print(f"Router model: {os.getenv('ROUTER_LLM_MODEL_ID')}")
print(f"Sending query: '{test_input['query']}'")
start = time.time()
try:
    plan = _llm_route(test_input)
    elapsed = time.time() - start
    print(f"\nSUCCESS in {elapsed:.1f}s!")
    print(f"Workflow: {plan.workflow}")
    print(f"Intent: {plan.intent}")
    for g in plan.parallel_groups:
        tools = [s.tool for s in g.steps]
        print(f"  Group '{g.group_id}': {tools}")
    if plan.skipped_tools:
        for s in plan.skipped_tools:
            print(f"  Skipped: {s.tool} - {s.reason}")
except Exception as e:
    elapsed = time.time() - start
    print(f"\nFAILED in {elapsed:.1f}s: {e}")
