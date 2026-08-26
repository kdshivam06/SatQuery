"""FINAL recovery: extract ALL project files from transcript and force-overwrite everything."""
import json
from pathlib import Path

TRANSCRIPT = r"C:\Users\Akshara\.gemini\antigravity-ide\brain\5d7e2b2d-e081-40c8-98dd-9b860903827b\.system_generated\logs\transcript_full.jsonl"
PROJECT = r"c:\Users\Akshara\Downloads\sih26\SatQuery"

# ALL files that should exist (every file created/rewritten this session)
ALL_PROJECT_FILES = [
    "backend/.env.example",
    "backend/api/schemas.py",
    "backend/tools/base_tool.py",
    "backend/tools/utils.py",
    "backend/tools/metadata_tool.py",
    "backend/tools/preview_tool.py",
    "backend/tools/ndvi_tool.py",
    "backend/tools/ndwi_tool.py",
    "backend/tools/mndwi_tool.py",
    "backend/tools/ndbi_tool.py",
    "backend/tools/sar_water_tool.py",
    "backend/tools/sar_builtup_tool.py",
    "backend/tools/change_map_tool.py",
    "backend/tools/mask_fusion_tool.py",
    "backend/tools/area_calculator_tool.py",
    "backend/tools/overlay_tool.py",
    "backend/tools/custom_dual_encoder_tool.py",
    "backend/tools/croma_tool.py",
    "backend/tools/remoteclip_tool.py",
    "backend/tools/geochat_tool.py",
    "backend/tools/teochat_tool.py",
    "backend/tools/segearth_tool.py",
    "backend/tools/sarclip_tool.py",
    "backend/tools/registry.py",
    "backend/agent/planner_schema.py",
    "backend/agent/context_builder.py",
    "backend/agent/fallback_router.py",
    "backend/agent/router_llm.py",
    "backend/agent/resource_scheduler.py",
    "backend/agent/trace_logger.py",
    "backend/agent/confidence.py",
    "backend/agent/executor.py",
    "backend/agent/fusion.py",
    "backend/agent/controller.py",
    "backend/reports/__init__.py",
    "backend/reports/report_builder.py",
    "backend/api/routes_analyze.py",
    "backend/api/routes_runs.py",
    "backend/main.py",
    "frontend/index.html",
    "requirements.txt",
    "test_smoke.py",
    "create_test_data.py",
]

def normalize(path):
    return path.replace("\\", "/").lower().rstrip("/")

def main():
    norm_project = normalize(PROJECT)
    # Collect LAST version of every file from transcript
    file_contents = {}

    with open(TRANSCRIPT, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                step = json.loads(line)
            except json.JSONDecodeError:
                continue

            for tc in step.get("tool_calls", []):
                name = tc.get("name", "") or tc.get("tool_name", "")
                if name != "write_to_file":
                    continue
                args = tc.get("arguments", {}) or tc.get("args", {})
                if not args:
                    continue

                target = args.get("TargetFile", "")
                content = args.get("CodeContent", "")
                if not target or not content:
                    continue

                norm_target = normalize(target)
                if norm_target.startswith(norm_project):
                    rel = target[len(PROJECT):].lstrip("/").lstrip("\\")
                else:
                    rel = target

                rel_norm = normalize(rel)
                file_contents[rel_norm] = (rel, content)

    # Force-write ALL project files
    restored = 0
    not_found = []
    for rel in ALL_PROJECT_FILES:
        key = normalize(rel)
        if key in file_contents:
            orig_rel, content = file_contents[key]
            out_path = Path(PROJECT) / orig_rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            print(f"  OK: {orig_rel}")
            restored += 1
        else:
            not_found.append(rel)
            print(f"  MISSING FROM TRANSCRIPT: {rel}")

    print(f"\nRestored {restored}/{len(ALL_PROJECT_FILES)} files.")
    if not_found:
        print(f"Not found in transcript: {not_found}")

if __name__ == "__main__":
    main()
