from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
from src.schema import AISuggestionResponse

# Rule signature: (parsed, expected_model, context) -> list[str] (errors)
RuleFn = Callable[[AISuggestionResponse, AISuggestionResponse, Optional[Dict[str, Any]]], List[str]]


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


def _get_attr(obj: Any, name: str):
    if obj is None:
        return None
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name)
    try:
        return obj.get(name)
    except Exception:
        return None


###################
# Generic rules
###################

def rule_instance_check(allow_none_only: bool = False) -> RuleFn:
    def _rule(parsed, expected, context):
        if parsed is None:
            return [] if allow_none_only else ["Parsed result is None"]
        if not hasattr(parsed, "items"):
            return ["Parsed result not AISuggestionResponse-like (missing .items)"]
        return []
    return _rule


def rule_item_count_leq(max_items: int) -> RuleFn:
    def _rule(parsed, expected, context):
        n = len(getattr(parsed, "items", []) or [])
        if n > max_items:
            return [f"Too many items: parsed={n}, allowed<={max_items}"]
        return []
    return _rule


def rule_item_count_eq(eq: int) -> RuleFn:
    def _rule(parsed, expected, context):
        n = len(getattr(parsed, "items", []) or [])
        if n != eq:
            return [f"Item count mismatch: parsed={n}, expected={eq}"]
        return []
    return _rule


def rule_confidence_range() -> RuleFn:
    def _rule(parsed, expected, context):
        c = _get_attr(parsed, "confidence")
        if c is None:
            return []
        try:
            if not (0.0 <= float(c) <= 1.0):
                return [f"Confidence out of range: {c}"]
        except Exception:
            return [f"Confidence not numeric: {c}"]
        return []
    return _rule


def rule_confidence_max(max_conf: float) -> RuleFn:
    def _rule(parsed, expected, context):
        c = _get_attr(parsed, "confidence")
        if c is None:
            return []
        try:
            if float(c) > max_conf:
                return [f"Confidence too high for no-slot case: {c} > {max_conf}"]
        except Exception:
            return [f"Confidence not numeric: {c}"]
        return []
    return _rule


def rule_required_item_fields(fields: List[str]) -> RuleFn:
    def _rule(parsed, expected, context):
        errs = []
        items = getattr(parsed, "items", []) or []
        for idx, it in enumerate(items):
            for f in fields:
                val = _get_attr(it, f)
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    errs.append(f"Item {idx} missing required field '{f}'")
        return errs
    return _rule


def rule_at_least_one_item_type(type_v: int) -> RuleFn:
    def _rule(parsed, expected, context):
        items = getattr(parsed, "items", []) or []
        for it in items:
            if _get_attr(it, "item_type") == type_v:
                return []
        return [f"No item with item_type={type_v} found"]
    return _rule


def rule_no_item_type(type_v: int) -> RuleFn:
    def _rule(parsed, expected, context):
        items = getattr(parsed, "items", []) or []
        if any(_get_attr(it, "item_type") == type_v for it in items):
            return [f"Unexpected item_type={type_v} present"]
        return []
    return _rule


def rule_parent_null_for_item_type(item_type: int) -> RuleFn:
    def _rule(parsed, expected, context):
        items = getattr(parsed, "items", []) or []
        for it in items:
            if _get_attr(it, "item_type") == item_type and _get_attr(it, "parentTaskId") is None:
                return []
        return [f"No item_type={item_type} found with parentTaskId=null"]
    return _rule


def rule_parent_equals(item_type: int, parent_id: str) -> RuleFn:
    def _rule(parsed, expected, context):
        items = getattr(parsed, "items", []) or []
        for it in items:
            if _get_attr(it, "item_type") == item_type and str(_get_attr(it, "parentTaskId")) == str(parent_id):
                return []
        return [f"No item_type={item_type} found with parentTaskId={parent_id}"]
    return _rule


def rule_deadline_before(limit_iso: str, item_type: Optional[int] = None, allow_equal: bool = True) -> RuleFn:
    limit_dt = _parse_iso(limit_iso)
    def _rule(parsed, expected, context):
        if limit_dt is None:
            return [f"Invalid limit datetime: {limit_iso}"]
        errs = []
        items = getattr(parsed, "items", []) or []
        for idx, it in enumerate(items):
            if item_type is None or _get_attr(it, "item_type") == item_type:
                d = _parse_iso(_get_attr(it, "deadline"))
                if d is None:
                    continue
                if allow_equal:
                    if d > limit_dt:
                        errs.append(f"Item {idx} deadline too late: {d.isoformat()} > {limit_dt.isoformat()}")
                else:
                    if d >= limit_dt:
                        errs.append(f"Item {idx} deadline not strictly before {limit_dt.isoformat()}")
        return errs
    return _rule


def rule_estimated_leq(max_minutes: int, item_type: Optional[int] = None) -> RuleFn:
    def _rule(parsed, expected, context):
        errs = []
        for idx, it in enumerate(getattr(parsed, "items", []) or []):
            if item_type is None or _get_attr(it, "item_type") == item_type:
                em = _get_attr(it, "estimated_minutes")
                if em is None:
                    continue
                try:
                    if int(em) > max_minutes:
                        errs.append(f"Item {idx} estimated_minutes too large: {em} > {max_minutes}")
                except Exception:
                    errs.append(f"Item {idx} estimated_minutes not numeric: {em}")
        return errs
    return _rule


def rule_reason_contains(keywords: List[str], any_of: bool = True, where: str = "global") -> RuleFn:
    kws = [k.lower() for k in keywords]
    def _rule(parsed, expected, context):
        def has(txt):
            if not txt: return False
            t = str(txt).lower()
            return any(k in t for k in kws) if any_of else all(k in t for k in kws)
        if where in ("global", "either") and has(_get_attr(parsed, "reason")):
            return []
        if where in ("item", "either"):
            for it in getattr(parsed, "items", []) or []:
                if has(_get_attr(it, "reason")):
                    return []
        return [f"Reason does not contain expected keywords {keywords} (where={where})"]
    return _rule


def rule_reason_match_expected() -> RuleFn:
    def _rule(parsed, expected, context):
        p_reason = (_get_attr(parsed, "reason") or "").strip().lower()
        e_reason = (_get_attr(expected, "reason") or "").strip().lower()
        if not p_reason or not e_reason:
            return []
        if e_reason not in p_reason:
            return [f"Reason mismatch: parsed='{p_reason}' expected~='{e_reason}'"]
        return []
    return _rule


def rule_avoid_time_range(start_iso: str, end_iso: str) -> RuleFn:
    start_dt = _parse_iso(start_iso)
    end_dt = _parse_iso(end_iso)
    def _rule(parsed, expected, context):
        if not start_dt or not end_dt:
            return [f"Invalid time range: {start_iso} - {end_iso}"]
        errs = []
        for idx, it in enumerate(getattr(parsed, "items", []) or []):
            for k in ("deadline", "startUtc", "endUtc"):
                d = _parse_iso(_get_attr(it, k))
                if d and start_dt <= d <= end_dt:
                    errs.append(f"Item {idx} {k}={d.isoformat()} overlaps forbidden {start_dt.isoformat()}-{end_dt.isoformat()}")
        return errs
    return _rule


def rule_timeout_and_retry(timeout_ms: int = 15000) -> RuleFn:
    def _rule(parsed, expected, context):
        meta = _get_attr(parsed, "metadata") or {}
        errs = []
        resp_ms = meta.get("response_ms") if isinstance(meta, dict) else None
        retries = meta.get("retries") if isinstance(meta, dict) else None
        if resp_ms:
            try:
                if int(resp_ms) > timeout_ms and not (retries and int(retries) >= 1):
                    errs.append(f"response_ms {resp_ms} > {timeout_ms} without retry")
            except Exception:
                errs.append(f"Invalid response_ms: {resp_ms}")
        else:
            # allow pass if expected had timeout case
            return []
        return errs
    return _rule


########################
# COMMON RULES
########################
COMMON_RULES: List[RuleFn] = [
    rule_instance_check(),
    rule_confidence_range(),
    rule_required_item_fields(["item_type", "title"]),
]


########################
# MAPPING TC -> RULES
########################
RULES: Dict[str, List[RuleFn]] = {
    "tc01": [
        rule_item_count_leq(3),
        rule_at_least_one_item_type(0),
        rule_deadline_before("2025-09-25T15:00:00Z", item_type=0),
        rule_estimated_leq(120, item_type=0),
        rule_reason_contains("sang", where="either"),
    ],
    "tc02": [
        rule_item_count_leq(3),
        rule_at_least_one_item_type(1),
        rule_parent_null_for_item_type(1),
        rule_estimated_leq(120, item_type=1),
        rule_reason_contains("checklist", where="either"),
        # rule_no_item_type(0),
    ],
    "tc03": [
        rule_item_count_leq(3),
        rule_at_least_one_item_type(1),
        rule_parent_equals(1, "11111111-aaaa-bbbb-cccc-000000000010"),
        rule_deadline_before("2025-09-27T09:00:00Z", item_type=1),
        rule_reason_contains(["tiep tuc", "lien quan", "hien co"], where="either"),
        # rule_no_item_type(0),
    ],
    "tc04": [
        rule_item_count_eq(0),
        rule_confidence_max(0.2),
        rule_reason_match_expected(),
    ],
    "tc05": [
        rule_item_count_leq(3),
        rule_at_least_one_item_type(0),
        rule_deadline_before("2025-09-25T15:30:00Z"),
        rule_reason_contains(["toi", "night", "night_owl", "cu dem"], where="either"),
    ],
    "tc06": [
        rule_item_count_leq(3),
        rule_avoid_time_range("2025-09-25T07:00:00Z", "2025-09-25T11:00:00Z"),
        rule_reason_contains(["11:30", "slot 11:30"], where="either"),
    ],
    "tc07": [rule_instance_check(allow_none_only=True)],
    "tc08": [rule_required_item_fields(["item_type", "title"])],
    "tc09": [rule_item_count_leq(3)],
    "tc10": [rule_timeout_and_retry(15000)],
}
