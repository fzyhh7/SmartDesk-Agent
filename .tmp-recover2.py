from pathlib import Path

ignore_dirs = {".git", ".git-portable", ".venv", "node_modules", ".data", "deploy/data"}
ext_ok = {".py", ".md", ".ts", ".vue", ".html", ".css", ".json", ".jsonl", ".toml", ".yml", ".yaml", ".txt", ".example"}

for p in Path(".").rglob("*"):
    if not p.is_file():
        continue
    rel = p.as_posix()
    if any(rel.startswith(d + "/") or rel == d for d in ignore_dirs):
        continue
    if p.name.startswith(".tmp-"):
        continue
    if p.suffix in ext_ok or p.name in {".gitignore", "LICENSE", ".env.example"}:
        raw = p.read_bytes()
        has_bom = raw.startswith(b"\xef\xbb\xbf")
        if has_bom:
            raw = raw[3:]
            p.write_bytes(raw)
        try:
            txt = raw.decode("utf-8")
        except Exception as e:
            print(f"INVALID UTF-8: {rel} -> {e}")
            continue
        # Check for typical GBK-in-UTF8 mojibake chars
        suspect = sum(1 for ch in txt if ch in "路浼笟儴鏈嶅姟鍙鐢ㄨ嚜鐒惰瑷€闂埗搴")
        if has_bom or "\ufffd" in txt:
            print(f"FIXED BOM / CHECK {rel}: bom={has_bom}, fffd={'\ufffd' in txt}")
print("Scan complete.")
