import json
from src.schema import AISuggestionResponse
from src.llm_client import llm
from src.rules.ai_rules import RULES, COMMON_RULES
from typing import Optional, Dict, Any, List 
from datetime import datetime, timezone

# Configurable thresholds
CONFIDENCE_TOLERANCE = 0.20
ALLOW_ALTERNATIVE_ITEM_TYPES = {
    # expected_item_type: [acceptable_alternatives]
    # e.g., checklist (1) can be accepted as task (0) with warning
    1: [0],
}
PARENT_NULL_STRICT = True  # if True: expected parentTaskId == None requires parsed parentTaskId == None


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    try:
        if isinstance(s, str) and s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _get_attr(obj, name, default=None):
    if obj is None:
        return default
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    try:
        return obj.get(name, default)
    except Exception:
        return default


def compare_result(parsed: AISuggestionResponse, expected: dict, context: Optional[Dict[str, Any]] = None, tc: Optional[str] = None) -> List[str]:
    errors: List[str] = []

    # validate expected schema
    try:
        AISuggestionResponse.model_validate(expected)
    except Exception as e:
        return [f"Expected JSON invalid: {e}"]

    # apply common + tc-specific rules
    rules = COMMON_RULES.copy()
    if tc and tc in RULES:
        rules += RULES[tc]
    for rule in rules:
        try:
            rerrs = rule(parsed, expected, context)
            if rerrs:
                errors.extend(rerrs)
        except Exception as ex:
            errors.append(f"Rule {getattr(rule, '__name__', str(rule))} raised exception: {ex}")

    return errors




def run_test(tc: str):
    with open(f"src/context/{tc}.json", "r", encoding="utf-8") as f:
        context = json.load(f)
    with open(f"src/expected/{tc}.json", "r", encoding="utf-8") as f:
        expected = json.load(f)

    # call LLM with context -> returns AISuggestionResponse object
    parsed = llm(context)

    # Debug print (optional)
    print(f"\n=== RAW LLM OUTPUT for {tc} ===")
    try:
        print(parsed.model_dump_json(indent=2))
    except Exception:
        print(str(parsed))

    print(f"=== EXPECTED for {tc} ===")
    print(json.dumps(expected, indent=2, ensure_ascii=False))

    # Compare results
    errors = compare_result(parsed, expected, context=context, tc=tc)

    if errors:
        result = {
            "tc": tc,
            "status": "FAIL",
            "errors": errors,
            "expected": expected,
            "parsed": parsed.model_dump() if hasattr(parsed, "model_dump") else str(parsed)
        }
        print(f"[{tc}] ❌ FAILED content")
        for err in errors:
            print("   -", err)
    else:
        result = {
            "tc": tc,
            "status": "PASS",
            "expected": expected,
            "parsed": parsed.model_dump() if hasattr(parsed, "model_dump") else str(parsed)
        }
        print(f"[{tc}] ✅ PASSED (content match)")

    return result

