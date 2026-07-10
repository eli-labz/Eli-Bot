from pathlib import Path
import json
import re
import os
import threading
import hashlib
from collections import OrderedDict

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_DIR = Path(__file__).resolve().parent / "model" / "MiniCPM5-1B"
MODEL_NAME = "openbmb/MiniCPM5-1B"
_TOKENIZER = None
_MODEL = None
_DEVICE = str(os.environ.get("ELI_MODEL_DEVICE", "auto")).strip().lower()
if _DEVICE == "auto":
    _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_MODEL_DTYPE = str(os.environ.get("ELI_MODEL_DTYPE", "auto")).strip().lower()
_MAX_INPUT_TOKENS = max(128, int(str(os.environ.get("ELI_MODEL_MAX_INPUT_TOKENS", "4096")).strip() or "4096"))
_MAX_NEW_TOKENS_CAP = max(32, int(str(os.environ.get("ELI_MODEL_MAX_NEW_TOKENS_CAP", "1024")).strip() or "1024"))
_MODEL_THREADS = max(1, int(str(os.environ.get("ELI_MODEL_THREADS", "4")).strip() or "4"))
_MODEL_INTEROP_THREADS = max(1, int(str(os.environ.get("ELI_MODEL_INTEROP_THREADS", "1")).strip() or "1"))
_MODEL_COMPILE = str(os.environ.get("ELI_MODEL_COMPILE", "0")).strip().lower() in {"1", "true", "yes", "on"}
_MODEL_USE_FAST_TOKENIZER = str(os.environ.get("ELI_MODEL_USE_FAST_TOKENIZER", "1")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_MODEL_USE_CACHE = str(os.environ.get("ELI_MODEL_USE_CACHE", "1")).strip().lower() in {"1", "true", "yes", "on"}
_MODEL_TOP_P = float(str(os.environ.get("ELI_MODEL_TOP_P", "1.0")).strip() or "1.0")
_MODEL_REPETITION_PENALTY = float(str(os.environ.get("ELI_MODEL_REPETITION_PENALTY", "1.0")).strip() or "1.0")
_MODEL_ATTN_IMPLEMENTATION = str(os.environ.get("ELI_MODEL_ATTN_IMPLEMENTATION", "")).strip().lower()
_MODEL_QUANTIZATION = str(os.environ.get("ELI_MODEL_QUANTIZATION", "none")).strip().lower()
_MODEL_OOM_RETRIES = max(0, int(str(os.environ.get("ELI_MODEL_OOM_RETRIES", "1")).strip() or "1"))
_MODEL_GPU_MAX_MEMORY_MB = max(0, int(str(os.environ.get("ELI_MODEL_GPU_MAX_MEMORY_MB", "0")).strip() or "0"))
_MODEL_CPU_MAX_MEMORY_MB = max(0, int(str(os.environ.get("ELI_MODEL_CPU_MAX_MEMORY_MB", "0")).strip() or "0"))
_MODEL_WARMUP = str(os.environ.get("ELI_MODEL_WARMUP", "0")).strip().lower() in {"1", "true", "yes", "on"}
_MODEL_WARMUP_MAX_NEW_TOKENS = max(1, int(str(os.environ.get("ELI_MODEL_WARMUP_MAX_NEW_TOKENS", "8")).strip() or "8"))
_MODEL_LOG_PROFILE = str(os.environ.get("ELI_MODEL_LOG_PROFILE", "0")).strip().lower() in {"1", "true", "yes", "on"}
_MODEL_RESPONSE_CACHE_SIZE = max(0, int(str(os.environ.get("ELI_MODEL_RESPONSE_CACHE_SIZE", "128")).strip() or "128"))
_MODEL_LOAD_LOCK = threading.Lock()
_MODEL_MAX_CONCURRENT = max(1, int(str(os.environ.get("ELI_MODEL_MAX_CONCURRENT", "1")).strip() or "1"))
_MODEL_INFER_SEMAPHORE = threading.Semaphore(_MODEL_MAX_CONCURRENT)
_MODEL_CACHE_LOCK = threading.Lock()
_MODEL_RESPONSE_CACHE = OrderedDict()


def _resolve_torch_dtype():
    if _MODEL_DTYPE in {"float16", "fp16", "half"}:
        return torch.float16
    if _MODEL_DTYPE in {"bfloat16", "bf16"}:
        return torch.bfloat16
    if _MODEL_DTYPE in {"float32", "fp32"}:
        return torch.float32

    # Auto policy: use fp16 on CUDA, fp32 on CPU for compatibility.
    return torch.float16 if _DEVICE == "cuda" else torch.float32


def _configure_torch_runtime():
    try:
        torch.set_num_threads(_MODEL_THREADS)
    except Exception:
        pass
    try:
        torch.set_num_interop_threads(_MODEL_INTEROP_THREADS)
    except Exception:
        pass
    if _DEVICE == "cuda":
        try:
            torch.backends.cuda.matmul.allow_tf32 = True
        except Exception:
            pass
        try:
            torch.set_float32_matmul_precision("high")
        except Exception:
            pass
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def _looks_like_cuda_oom(exc: Exception) -> bool:
    text = str(exc or "").lower()
    return "out of memory" in text and "cuda" in text


def _clear_cuda_cache():
    if _DEVICE != "cuda":
        return
    try:
        torch.cuda.empty_cache()
    except Exception:
        pass


def _resolve_max_memory_map() -> dict:
    if _DEVICE != "cuda":
        return {}

    memory_map = {}
    if _MODEL_GPU_MAX_MEMORY_MB > 0:
        try:
            gpu_count = torch.cuda.device_count()
        except Exception:
            gpu_count = 0
        for index in range(max(0, gpu_count)):
            memory_map[index] = f"{_MODEL_GPU_MAX_MEMORY_MB}MiB"

    if _MODEL_CPU_MAX_MEMORY_MB > 0:
        memory_map["cpu"] = f"{_MODEL_CPU_MAX_MEMORY_MB}MiB"

    return memory_map


def _resolve_quantization_kwargs() -> dict:
    """Build optional quantization kwargs while staying resilient when bitsandbytes is unavailable."""
    quant = _MODEL_QUANTIZATION
    if _DEVICE != "cuda" or quant not in {"8bit", "4bit"}:
        return {}

    try:
        from transformers import BitsAndBytesConfig
    except Exception:
        return {}

    if quant == "8bit":
        return {
            "quantization_config": BitsAndBytesConfig(load_in_8bit=True),
        }

    return {
        "quantization_config": BitsAndBytesConfig(load_in_4bit=True),
    }


def _cache_lookup(cache_key: str):
    if not cache_key or _MODEL_RESPONSE_CACHE_SIZE <= 0:
        return None
    with _MODEL_CACHE_LOCK:
        value = _MODEL_RESPONSE_CACHE.get(cache_key)
        if value is None:
            return None
        _MODEL_RESPONSE_CACHE.move_to_end(cache_key)
        return value


def _cache_store(cache_key: str, value: str):
    if not cache_key or _MODEL_RESPONSE_CACHE_SIZE <= 0:
        return
    with _MODEL_CACHE_LOCK:
        _MODEL_RESPONSE_CACHE[cache_key] = value
        _MODEL_RESPONSE_CACHE.move_to_end(cache_key)
        while len(_MODEL_RESPONSE_CACHE) > _MODEL_RESPONSE_CACHE_SIZE:
            _MODEL_RESPONSE_CACHE.popitem(last=False)


def _build_response_cache_key(normalized_messages, temperature: float, max_tokens: int) -> str:
    # Cache deterministic calls only.
    if float(temperature) > 0:
        return ""
    payload = {
        "messages": normalized_messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "input_cap": _MAX_INPUT_TOKENS,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _log_runtime_profile_once(model):
    if not _MODEL_LOG_PROFILE:
        return
    setattr(_log_runtime_profile_once, "_logged", getattr(_log_runtime_profile_once, "_logged", False))
    if getattr(_log_runtime_profile_once, "_logged", False):
        return

    param_dtype = "unknown"
    try:
        param_dtype = str(next(model.parameters()).dtype)
    except Exception:
        pass

    print(
        "MiniCPM runtime profile:",
        {
            "device": _DEVICE,
            "dtype": _MODEL_DTYPE,
            "effective_param_dtype": param_dtype,
            "quantization": _MODEL_QUANTIZATION,
            "max_input_tokens": _MAX_INPUT_TOKENS,
            "max_new_tokens_cap": _MAX_NEW_TOKENS_CAP,
            "max_concurrent": _MODEL_MAX_CONCURRENT,
            "threads": _MODEL_THREADS,
            "interop_threads": _MODEL_INTEROP_THREADS,
            "oom_retries": _MODEL_OOM_RETRIES,
            "cache_size": _MODEL_RESPONSE_CACHE_SIZE,
        },
    )
    setattr(_log_runtime_profile_once, "_logged", True)


def _run_model_warmup(tokenizer, model):
    if not _MODEL_WARMUP:
        return
    setattr(_run_model_warmup, "_warmed", getattr(_run_model_warmup, "_warmed", False))
    if getattr(_run_model_warmup, "_warmed", False):
        return

    try:
        warmup_prompt = tokenizer.apply_chat_template(
            [{"role": "user", "content": "ping"}],
            tokenize=False,
            add_generation_prompt=True,
        )
        warmup_inputs = tokenizer(
            warmup_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=min(256, _MAX_INPUT_TOKENS),
        )
        warmup_inputs = warmup_inputs.to(_resolve_model_input_device(model))
        with torch.inference_mode():
            _ = model.generate(
                **warmup_inputs,
                do_sample=False,
                max_new_tokens=_MODEL_WARMUP_MAX_NEW_TOKENS,
                pad_token_id=tokenizer.eos_token_id,
                use_cache=_MODEL_USE_CACHE,
            )
    except Exception:
        # Warmup should never break startup.
        pass
    finally:
        setattr(_run_model_warmup, "_warmed", True)


def _resolve_model_input_device(model):
    """Route inputs to the primary execution device, including accelerate-sharded models."""
    if _DEVICE != "cuda":
        return _DEVICE

    try:
        device_map = getattr(model, "hf_device_map", None)
        if isinstance(device_map, dict):
            for mapped in device_map.values():
                mapped_text = str(mapped).lower()
                if mapped_text.startswith("cuda"):
                    return mapped
    except Exception:
        pass

    return "cuda:0"


def _load_model():
    global _TOKENIZER, _MODEL
    if _TOKENIZER is not None and _MODEL is not None:
        return _TOKENIZER, _MODEL

    with _MODEL_LOAD_LOCK:
        if _TOKENIZER is not None and _MODEL is not None:
            return _TOKENIZER, _MODEL

        if not MODEL_DIR.exists():
            raise FileNotFoundError(f"MiniCPM5-1B model directory not found: {MODEL_DIR}")

        _configure_torch_runtime()

        _TOKENIZER = AutoTokenizer.from_pretrained(
            str(MODEL_DIR),
            use_fast=_MODEL_USE_FAST_TOKENIZER,
            local_files_only=True,
        )
        dtype = _resolve_torch_dtype()

        model_kwargs = {
            "torch_dtype": dtype,
            "low_cpu_mem_usage": True,
            "local_files_only": True,
        }
        if _MODEL_ATTN_IMPLEMENTATION:
            model_kwargs["attn_implementation"] = _MODEL_ATTN_IMPLEMENTATION
        model_kwargs.update(_resolve_quantization_kwargs())
        if _DEVICE == "cuda":
            # Let transformers shard/load efficiently on available CUDA memory.
            model_kwargs["device_map"] = "auto"
            max_memory_map = _resolve_max_memory_map()
            if max_memory_map:
                model_kwargs["max_memory"] = max_memory_map

        _MODEL = AutoModelForCausalLM.from_pretrained(str(MODEL_DIR), **model_kwargs)
        if _DEVICE != "cuda":
            _MODEL.to(_DEVICE)
        _MODEL.eval()

        if _MODEL_COMPILE:
            try:
                _MODEL = torch.compile(_MODEL)
            except Exception:
                # Keep runtime resilient even when compile backend is unavailable.
                pass

        _log_runtime_profile_once(_MODEL)
        _run_model_warmup(_TOKENIZER, _MODEL)

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

        max_new_tokens = min(max(1, int(max_tokens)), _MAX_NEW_TOKENS_CAP)
        cache_key = _build_response_cache_key(normalized_messages, float(temperature), max_new_tokens)
        cached_response = _cache_lookup(cache_key)
        if cached_response is not None:
            return cached_response

        prompt = tokenizer.apply_chat_template(
            normalized_messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        tokenizer_kwargs = {
            "return_tensors": "pt",
            "truncation": True,
            "max_length": _MAX_INPUT_TOKENS,
        }
        model_inputs = tokenizer(prompt, **tokenizer_kwargs)
        input_device = _resolve_model_input_device(model)
        model_inputs = model_inputs.to(input_device)

        do_sample = temperature > 0
        generation_kwargs = {
            "do_sample": do_sample,
            "temperature": max(0.01, float(temperature)),
            "max_new_tokens": max_new_tokens,
            "pad_token_id": tokenizer.eos_token_id,
            "use_cache": _MODEL_USE_CACHE,
            "top_p": max(0.05, min(1.0, _MODEL_TOP_P)),
            "repetition_penalty": max(0.9, _MODEL_REPETITION_PENALTY),
        }

        with _MODEL_INFER_SEMAPHORE:
            current_max_new = max_new_tokens
            output_ids = None
            for attempt in range(_MODEL_OOM_RETRIES + 1):
                try:
                    with torch.inference_mode():
                        output_ids = model.generate(
                            **model_inputs,
                            **{**generation_kwargs, "max_new_tokens": current_max_new},
                        )
                    break
                except RuntimeError as generation_error:
                    if not _looks_like_cuda_oom(generation_error) or attempt >= _MODEL_OOM_RETRIES:
                        raise
                    _clear_cuda_cache()
                    current_max_new = max(32, current_max_new // 2)

            if output_ids is None:
                raise RuntimeError("MiniCPM generation failed to produce output IDs.")

        generated_ids = output_ids[0][model_inputs["input_ids"].shape[-1]:]
        decision = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        decision = _strip_reasoning(decision)
        _cache_store(cache_key, decision)
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