import os
import json

# Indicators of compromise
malicious_files = ["setup_bun.js", "bun_environment.js"]
malicious_keywords = ["SHA1HULUD", "Shai-Hulud"]
suspicious_scripts = ["preinstall"]

report = {
    "malicious_files_found": [],
    "malicious_keywords_found": [],
    "suspicious_scripts_found": []
}

def scan_node_modules(base_path):
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file in malicious_files:
                report["malicious_files_found"].append(os.path.join(root, file))
            try:
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for keyword in malicious_keywords:
                        if keyword in content:
                            report["malicious_keywords_found"].append(file_path)
                            break
            except Exception:
                continue

def scan_package_lock(lock_file):
    try:
        with open(lock_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for pkg_name, pkg_info in data.get("packages", {}).items():
                scripts = pkg_info.get("scripts", {})
                for script_name in scripts.keys():
                    if script_name in suspicious_scripts:
                        report["suspicious_scripts_found"].append({"package": pkg_name, "script": script_name})
    except Exception as e:
        print(f"Error reading {lock_file}: {e}")

node_modules_path = "node_modules"
package_lock_path = "package-lock.json"

if os.path.exists(node_modules_path):
    scan_node_modules(node_modules_path)
else:
    print("node_modules directory not found.")

if os.path.exists(package_lock_path):
    scan_package_lock(package_lock_path)
else:
    print("package-lock.json not found.")

print("Scan Report:")
print(json.dumps(report, indent=4))

