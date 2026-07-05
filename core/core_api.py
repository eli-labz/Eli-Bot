from pathlib import Path
import json
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_DIR = Path(__file__).resolve().parent / "model" / "MiniCPM5-1B"
MODEL_NAME = "openbmb/MiniCPM5-1B"
_TOKENIZER = None
_MODEL = None
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def _load_model():
    global _TOKENIZER, _MODEL
    if _TOKENIZER is not None and _MODEL is not None:
        return _TOKENIZER, _MODEL

    if not MODEL_DIR.exists():
        raise FileNotFoundError(f"MiniCPM5-1B model directory not found: {MODEL_DIR}")

    _TOKENIZER = AutoTokenizer.from_pretrained(str(MODEL_DIR), use_fast=True)
    dtype = torch.float16 if _DEVICE == "cuda" else torch.float32
    _MODEL = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR),
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    _MODEL.to(_DEVICE)
    _MODEL.eval()
    return _TOKENIZER, _MODEL


def _normalize_messages(messages):
    normalized = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role not in {"system", "user", "assistant"}:
            role = "user"
        normalized.append({"role": role, "content": str(content)})
    return normalized


def _strip_reasoning(text):
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Handle unclosed think blocks by dropping from the opening tag onward.
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def _extract_balanced_json(text):
    starts = [i for i, ch in enumerate(text) if ch in "[{"]
    for start in starts:
        stack = []
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch in "[{":
                stack.append(ch)
            elif ch in "]}":
                if not stack:
                    break
                opener = stack.pop()
                if (opener == "{" and ch != "}") or (opener == "[" and ch != "]"):
                    break
                if not stack:
                    return text[start:i + 1]
    return None


def _extract_json_candidate(text):
    fence_patterns = [
        r"```json\s*(.*?)\s*```",
        r"```\s*(.*?)\s*```",
    ]
    for pattern in fence_patterns:
        match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return _extract_balanced_json(text)


def _repair_json_text(text):
    repaired = text.strip()
    # Remove common trailing commas that break JSON decoding.
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return repaired


def _normalize_actions_json(data):
    if isinstance(data, dict):
        if "actions" in data and isinstance(data["actions"], list):
            return data
        if "act" in data or "step" in data or "details" in data:
            return {"actions": [data]}
    if isinstance(data, list):
        return {"actions": data}
    raise ValueError("JSON must be an object or list compatible with actions.")


def _parse_planner_json(raw_text):
    cleaned = _strip_reasoning(raw_text)
    candidate = _extract_json_candidate(cleaned)
    if not candidate:
        raise ValueError("No JSON object found in model output.")

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        data = json.loads(_repair_json_text(candidate))

    return _normalize_actions_json(data)


def api_call(messages, model_name=MODEL_NAME, temperature=0.5, max_tokens=150):
    # model_name is kept for backward compatibility with existing calls.
    _ = model_name
    try:
        tokenizer, model = _load_model()
        normalized_messages = _normalize_messages(messages)

        prompt = tokenizer.apply_chat_template(
            normalized_messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        model_inputs = tokenizer(prompt, return_tensors="pt").to(_DEVICE)

        with torch.inference_mode():
            output_ids = model.generate(
                **model_inputs,
                do_sample=temperature > 0,
                temperature=max(0.01, float(temperature)),
                max_new_tokens=max(1, int(max_tokens)),
                pad_token_id=tokenizer.eos_token_id,
            )

        generated_ids = output_ids[0][model_inputs["input_ids"].shape[-1]:]
        decision = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        decision = _strip_reasoning(decision)
        return decision
    except Exception as e:
        raise Exception(f"An error occurred while running MiniCPM5-1B locally: {e}")


def api_call_json(messages, model_name=MODEL_NAME, temperature=0.2, max_tokens=512, retries=1):
    last_error = None
    current_messages = list(messages)

    for _ in range(retries + 1):
        raw = api_call(
            current_messages,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            normalized = _parse_planner_json(raw)
            return json.dumps(normalized)
        except Exception as parse_error:
            last_error = parse_error
            current_messages = current_messages + [
                {
                    "role": "assistant",
                    "content": raw,
                },
                {
                    "role": "user",
                    "content": (
                        "Return ONLY valid minified JSON with either an 'actions' array or an object with 'act' and 'step'. "
                        "No explanations, no markdown, no extra text."
                    ),
                },
            ]

    raise Exception(f"An error occurred while parsing planner JSON: {last_error}")


# # Replace this payload with the actual messages sequence for your use case # # Test
# messages_payload = [
#     {"role": "system", "content": "You are a helpful and knowledgeable assistant. Always uwufy the text."},
#     {"role": "user", "content": "Please help me troubleshoot my JavaScript code."}
# ]
#
# # Example configuration: you might want to specify 'temperature' for more creative responses,
# # or 'max_tokens' for more concise outputs
# result = api_call(messages_payload, temperature=0.7, max_tokens=100)
# print(f"AI Analysis Result: '{result}'")