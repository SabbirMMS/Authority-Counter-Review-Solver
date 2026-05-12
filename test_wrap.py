def _get_context_at(line: str, pos: int, state: str | None, language: str) -> str | None:
    quote: str | None = None
    escaped = False
    idx = 0
    current_state = state

    while idx <= pos and idx < len(line):
        ch = line[idx]
        
        if current_state == "/*":
            if idx + 1 < len(line) and ch == "*" and line[idx + 1] == "/":
                idx += 2
                current_state = None
                continue
            if idx == pos: return "/*"
            idx += 1
            continue
        elif current_state == '"""':
            if not escaped and idx + 2 < len(line) and line[idx:idx + 3] == '"""':
                idx += 3
                current_state = None
                continue
            if ch == "\\": escaped = not escaped
            else: escaped = False
            if idx == pos: return '"""'
            idx += 1
            continue
        elif current_state == "'''":
            if not escaped and idx + 2 < len(line) and line[idx:idx + 3] == "'''":
                idx += 3
                current_state = None
                continue
            if ch == "\\": escaped = not escaped
            else: escaped = False
            if idx == pos: return "'''"
            idx += 1
            continue
            
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            if idx == pos: return quote
            idx += 1
            continue
            
        if ch in {'"', "'", "`"}:
            if idx + 2 < len(line) and line[idx:idx + 3] == ch * 3:
                current_state = ch * 3
                idx += 3
                if idx - 1 >= pos: return current_state
                continue
            quote = ch
            if idx == pos: return quote
            idx += 1
            continue
            
        if ch == "#":
            if idx <= pos: return "#"
            break
            
        if language != "python":
            if idx + 1 < len(line) and ch == "/" and line[idx + 1] == "/":
                if idx <= pos: return "//"
                break
            
            if idx + 1 < len(line) and ch == "/" and line[idx + 1] == "*":
                current_state = "/*"
                idx += 2
                if idx - 1 >= pos: return "/*"
                continue
            
        if idx == pos: return None
        idx += 1
        
    return None

lines = [
    ('        // If opacity is "auto", then opacity will be changed if image and thumbnail have different aspect ratios', 101),
    ('            \'webkitAllowFullScreen mozallowfullscreen allowFullScreen allowtransparency="true" src=""></iframe>\',', 95),
]

for line, pos in lines:
    ctx = _get_context_at(line, pos, None, "javascript")
    print(f"Line: {line[:pos]}[X]{line[pos+1:]}")
    print(f"Context: {ctx}")
    
