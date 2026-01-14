def normalize_phone(s: str) -> str:
    cleaned = ''.join(filter(str.isdigit, s))
    if len(cleaned) == 10:
        return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"
    elif len(cleaned) == 11 and cleaned.startswith('1'):
        cleaned = cleaned[1:]
        return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"
    else:
        raise ValueError("Invalid phone number format")