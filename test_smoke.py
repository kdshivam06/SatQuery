"""Quick import smoke test for all SatQuery modules."""
import sys

try:
    from backend.tools.registry import TOOL_REGISTRY, get_enabled_tools, get_registry_summary_for_router
    print(f"Registry: {len(TOOL_REGISTRY)} entries")
    enabled = get_enabled_tools()
    print(f"Enabled: {len(enabled)}")
    summary = get_registry_summary_for_router()
    print(f"Router summary: {len(summary)} tools")
    for name in sorted(summary):
        info = summary[name]
        print(f"  {name}: {info['run_mode']} -> {info['resource_lane']}")

    from backend.agent.controller import run_analysis
    from backend.agent.executor import execute_plan
    from backend.agent.fusion import fuse_results
    from backend.agent.router_llm import route
    from backend.agent.fallback_router import fallback_route
    print("\nAll modules import OK!")

    # Test fallback router
    test_input = {
        "query": "detect water bodies",
        "input_summary": {
            "image_count": 2,
            "modalities": ["sar", "multispectral"],
            "configuration": "cross_modal_pair",
            "available_bands": {"multispectral": ["B02", "B03", "B04", "B08"]},
        },
        "available_tools": list(summary.keys()),
    }
    plan = fallback_route(test_input)
    print(f"\nFallback router test:")
    print(f"  Workflow: {plan.workflow}")
    print(f"  Groups: {len(plan.parallel_groups)}")
    for g in plan.parallel_groups:
        print(f"    {g.group_id}: {[s.tool for s in g.steps]}")
    print(f"  Skipped: {[s.tool for s in plan.skipped_tools]}")
    print(f"  Total steps: {len(plan.all_steps())}")

except Exception as e:
    print(f"FAILED: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
