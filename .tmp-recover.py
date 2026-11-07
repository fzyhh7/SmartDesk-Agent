import json
import re
from pathlib import Path


def strip_line_nums(block: str) -> str:
    lines = []
    for line in block.splitlines():
        if line.startswith("(End of file") or line.startswith("(Showing lines"):
            continue
        m = re.match(r"^\s*\d+:\s?(.*)$", line)
        if m:
            lines.append(m.group(1))
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def get_last_read(dump_file: str, target_suffix: str) -> str:
    txt = Path(dump_file).read_text(encoding="utf-8")
    found = None
    for m in re.finditer(r"<path>([^<]+)</path>\s*<type>file</type>\s*<content>\n(.*?)\n</content>", txt, re.S):
        fpath, content = m.group(1), m.group(2)
        if fpath.replace("\\", "/").endswith(target_suffix) and not content.startswith(("Created file", "Updated file")):
            found = strip_line_nums(content)
    assert found is not None, f"Not found {target_suffix} in {dump_file}"
    return found


def get_last_write(dump_file: str, target_suffix: str) -> str:
    txt = Path(dump_file).read_text(encoding="utf-8")
    found = None
    for line in txt.splitlines():
        if '"file_path"' in line and '"content"' in line:
            try:
                obj = json.loads(line)
                fp = obj.get("file_path", "").replace("\\", "/")
                if fp.endswith(target_suffix):
                    found = obj["content"]
            except Exception:
                pass
    assert found is not None, f"Not found write {target_suffix} in {dump_file}"
    return found


# 1. README.md from .tmp-b47.txt
readme = get_last_read(".tmp-b47.txt", "README.md")
readme = readme.replace("SmartDesk AI", "SmartDesk-Agent").replace("smartdesk-ai", "SmartDesk-Agent")
Path("README.md").write_text(readme, encoding="utf-8", newline="\n")
print("Restored README.md:", len(readme), "chars")

# 2. LICENSE from .tmp-b47.txt
lic = get_last_read(".tmp-b47.txt", "LICENSE")
lic = lic.replace("SmartDesk AI", "SmartDesk-Agent").replace("smartdesk-ai", "SmartDesk-Agent")
Path("LICENSE").write_text(lic, encoding="utf-8", newline="\n")
print("Restored LICENSE:", len(lic), "chars")

# 3. pyproject.toml from .tmp-b47.txt
pyproj = get_last_read(".tmp-b47.txt", "pyproject.toml")
pyproj = pyproj.replace("SmartDesk AI", "SmartDesk-Agent").replace("smartdesk-ai", "SmartDesk-Agent")
Path("pyproject.toml").write_text(pyproj, encoding="utf-8", newline="\n")
print("Restored pyproject.toml:", len(pyproj), "chars")

# 4. deploy/docker-compose.yml from .tmp-b39.txt
dc = get_last_read(".tmp-b39.txt", "deploy/docker-compose.yml")
dc = dc.replace("SmartDesk AI", "SmartDesk-Agent").replace("smartdesk-ai", "SmartDesk-Agent")
Path("deploy/docker-compose.yml").write_text(dc, encoding="utf-8", newline="\n")
print("Restored deploy/docker-compose.yml:", len(dc), "chars")

# 5. frontend/src/components/SideNav.vue from .tmp-b30.txt
sidenav = get_last_write(".tmp-b30.txt", "frontend/src/components/SideNav.vue")
sidenav = sidenav.replace("SmartDesk AI", "SmartDesk-Agent").replace("smartdesk-ai", "SmartDesk-Agent")
Path("frontend/src/components/SideNav.vue").write_text(sidenav, encoding="utf-8", newline="\n")
print("Restored frontend/src/components/SideNav.vue:", len(sidenav), "chars")

# 6. backend/app/api/main.py from .tmp-b5.txt
main_py = get_last_read(".tmp-b5.txt", "backend/app/api/main.py")
main_py = main_py.replace("SmartDesk AI", "SmartDesk-Agent").replace("smartdesk-ai", "SmartDesk-Agent")
Path("backend/app/api/main.py").write_text(main_py, encoding="utf-8", newline="\n")
print("Restored backend/app/api/main.py:", len(main_py), "chars")

# 7. frontend/index.html
index_html = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SmartDesk-Agent · 企业服务台</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
"""
Path("frontend/index.html").write_text(index_html, encoding="utf-8", newline="\n")
print("Restored frontend/index.html:", len(index_html), "chars")
