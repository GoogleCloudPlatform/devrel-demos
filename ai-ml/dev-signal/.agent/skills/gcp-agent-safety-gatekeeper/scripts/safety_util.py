from google.cloud import modelarmor_v1
from google.cloud.modelarmor_v1.types import FilterMatchState

def parse_model_armor_response(response) -> list[str]:
    """Analyzes the Model Armor response and returns a list of detected filters."""
    sanitization_result = response.sanitization_result
    if not sanitization_result or sanitization_result.filter_match_state == FilterMatchState.NO_MATCH_FOUND:
        return []

    detected_filters = []
    filter_matches = sanitization_result.filter_results

    if "pi_and_jailbreak" in filter_matches:
        if filter_matches["pi_and_jailbreak"].pi_and_jailbreak_filter_result.match_state == FilterMatchState.MATCH_FOUND:
            detected_filters.append("Prompt Injection and Jailbreaking")

    if "malicious_uris" in filter_matches:
        if filter_matches["malicious_uris"].malicious_uri_filter_result.match_state == FilterMatchState.MATCH_FOUND:
            detected_filters.append("Malicious URIs")

    if "sdp" in filter_matches:
        sdp_result = filter_matches["sdp"].sdp_filter_result
        if sdp_result.inspect_result and sdp_result.inspect_result.match_state == FilterMatchState.MATCH_FOUND:
            for finding in sdp_result.inspect_result.findings:
                detected_filters.append(f"SDP: {finding.info_type}")

    if "rai" in filter_matches:
        rai_result = filter_matches["rai"].rai_filter_result
        for filter_name, matched in rai_result.rai_filter_type_results.items():
            if matched.match_state == FilterMatchState.MATCH_FOUND:
                detected_filters.append(f"RAI: {filter_name}")

    return detected_filters
