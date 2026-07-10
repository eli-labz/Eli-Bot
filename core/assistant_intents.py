from __future__ import annotations


def looks_like_open_word_request(raw_action: str) -> bool:
    normalized = str(raw_action or "").strip().lower()
    if not normalized:
        return False

    open_prefix = normalized.startswith("open ") or normalized.startswith("launch ") or normalized.startswith("start ")
    if not open_prefix:
        return False

    target = normalized.split(" ", 1)[1].strip() if " " in normalized else ""
    word_targets = {
        "word",
        "microsoft word",
        "ms word",
        "winword",
        "winword.exe",
        "microsoft office word",
    }
    return target in word_targets


def get_word_workflow_steps(raw_action: str) -> list[str]:
    normalized = str(raw_action or "").strip().lower()
    if not normalized:
        return []

    open_word_targets = {
        "word",
        "microsoft word",
        "ms word",
        "winword",
        "winword.exe",
        "microsoft office word",
    }
    create_document_suffixes = {
        "create a new document",
        "create new document",
        "create a document",
        "make a new document",
        "make new document",
        "new document",
    }

    prefixes = ("open ", "launch ", "start ")
    for prefix in prefixes:
        if not normalized.startswith(prefix):
            continue

        remainder = normalized[len(prefix):].strip()
        for target in open_word_targets:
            if remainder == target:
                return ["word open"]

            for joiner in (" and ", " then "):
                composite = f"{target}{joiner}"
                if not remainder.startswith(composite):
                    continue

                suffix = remainder[len(composite):].strip()
                if suffix in create_document_suffixes:
                    return ["word open", "word create document"]

                type_prefixes = ("type ", "write ")
                for type_prefix in type_prefixes:
                    if suffix.startswith(type_prefix):
                        text = raw_action.strip()[len(raw_action.strip()) - len(suffix) + len(type_prefix):].strip()
                        if text:
                            return ["word open", "word type " + text]

                save_as_prefixes = ("save as ", "save it as ")
                for save_as_prefix in save_as_prefixes:
                    if suffix.startswith(save_as_prefix):
                        path = raw_action.strip()[len(raw_action.strip()) - len(suffix) + len(save_as_prefix):].strip()
                        if path:
                            return ["word open", "word save as " + path]

    return []