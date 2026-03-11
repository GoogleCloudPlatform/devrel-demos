def _get_tool_calls(events: list) -> list:
    """Extracts tool names and inputs from an ADK reasoning trace."""
    tool_calls = []
    for event in events:
        parts = event.get("content", {}).get("parts", [])
        for part in parts:
            if "function_call" in part:
                fc = part["function_call"]
                tool_calls.append({"name": fc["name"], "args": fc.get("args", {})})
    return tool_calls

def trajectory_precision(instance: dict) -> float:
    """Measures percentage of predicted tools that were in the reference."""
    predicted = _get_tool_calls(instance.get("intermediate_events", []))
    reference = instance.get("reference_trajectory", [])
    
    if not predicted:
        return 0.0
        
    ref_names = {t["name"] for t in reference}
    matches = [t for t in predicted if t["name"] in ref_names]
    return len(matches) / len(predicted)

def trajectory_recall(instance: dict) -> float:
    """Measures percentage of reference tools that were predicted."""
    predicted = _get_tool_calls(instance.get("intermediate_events", []))
    reference = instance.get("reference_trajectory", [])
    
    if not reference:
        return 1.0
        
    pred_names = {t["name"] for t in predicted}
    matches = [t for t in reference if t["name"] in pred_names]
    return len(matches) / len(reference)

def in_order_match(instance: dict) -> float:
    """Checks if reference tools were called in the specified order."""
    predicted = [t["name"] for t in _get_tool_calls(instance.get("intermediate_events", []))]
    reference = [t["name"] for t in instance.get("reference_trajectory", [])]
    
    if not reference:
        return 1.0
        
    it = iter(predicted)
    if all(name in it for name in reference):
        return 1.0
    return 0.0
