def clp(val) -> str:
    try:
        return f"${int(val):,.0f}".replace(",", ".")
    except:
        return str(val)

def truncate(s: str, n: int = 38) -> str:
    return s[:n] if isinstance(s, str) else s
