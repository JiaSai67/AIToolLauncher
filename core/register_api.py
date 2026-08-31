import os
import json
import argparse

APPDATA_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "AI_Tool_Launcher")
os.makedirs(APPDATA_DIR, exist_ok=True)
REGISTRY_FILE = os.path.join(APPDATA_DIR, "registry.json")

def register_tool(name, desc, executable, cwd):
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"tools": []}
        
    # 避免重複註冊同名稱的工具
    data["tools"] = [t for t in data["tools"] if t.get("name") != name]
    
    data["tools"].append({
        "name": name,
        "description": desc,
        "executable": executable,
        "working_dir": cwd
    })
    
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Successfully registered '{name}' to {REGISTRY_FILE}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register a tool to the AI Tool Launcher.")
    parser.add_argument("--name", required=True, help="Tool name")
    parser.add_argument("--desc", default="", help="Tool description")
    parser.add_argument("--exec", required=True, dest="executable", help="Executable path (.bat, .py, .exe)")
    parser.add_argument("--cwd", required=True, help="Working directory for the tool")
    
    args = parser.parse_args()
    register_tool(args.name, args.desc, args.executable, args.cwd)
