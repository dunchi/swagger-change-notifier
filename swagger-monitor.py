#!/usr/bin/env python3
import subprocess
import requests
import hashlib
import os
import re
import json
from datetime import datetime

# 설정
SLACK_WEBHOOK = "YOUR_SLACK_WEBHOOK_URL"  # Slack Incoming Webhook URL
SPEC_STORE = os.path.expanduser("~/scripts/swagger-specs")  # 해시 저장 경로
EXCLUDE_APPS = ["keycloak-app", "config-app"]  # 제외할 컨테이너

def get_app_containers():
    """docker ps에서 *-app 컨테이너와 포트 추출"""
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}} {{.Ports}}"],
        capture_output=True, text=True
    )

    services = {}
    for line in result.stdout.strip().split("\n"):
        if not line or "-app" not in line:
            continue

        parts = line.split(" ", 1)
        name = parts[0]

        if name in EXCLUDE_APPS:
            continue

        ports_str = parts[1] if len(parts) > 1 else ""

        # 모든 호스트 포트 추출
        port_matches = re.findall(r"0\.0\.0\.0:(\d+)->(\d+)/tcp", ports_str)

        # API 포트 우선순위: 80xx, 81xx, 70xx, 60xx (디버그 포트 5xxx 제외)
        api_port = None
        for host_port, container_port in port_matches:
            if host_port.startswith(("80", "81", "70", "60")):
                api_port = host_port
                break

        if api_port:
            services[name] = f"http://localhost:{api_port}"

    return services

def check_swagger(name, base_url):
    """Swagger 스펙 가져와서 해시 비교"""
    try:
        resp = requests.get(f"{base_url}/v3/api-docs", timeout=5)
        if resp.status_code != 200:
            return None, None

        # JSON 파싱 후 키 정렬하여 정규화
        spec_data = resp.json()
        normalized_spec = json.dumps(spec_data, sort_keys=True)
        new_hash = hashlib.md5(normalized_spec.encode('utf-8')).hexdigest()

        hash_file = os.path.join(SPEC_STORE, f"{name}.hash")

        old_hash = ""
        if os.path.exists(hash_file):
            with open(hash_file, "r") as f:
                old_hash = f.read().strip()

        changed = new_hash != old_hash

        if changed:
            with open(hash_file, "w") as f:
                f.write(new_hash)

        return changed, old_hash == ""  # is_new
    except Exception as e:
        return None, None

def notify_slack(changes):
    """Slack으로 변경사항 알림"""
    if not changes:
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_items = [name.replace("-app", "") for name, is_new in changes if is_new]
    changed_items = [name.replace("-app", "") for name, is_new in changes if not is_new]

    lines = [f"*스웨거 스펙 알림* ({now})\n"]

    if new_items:
        lines.append("신규")
        for item in new_items:
            lines.append(f"- {item}")

    if changed_items:
        if new_items:
            lines.append("")
        lines.append("변경")
        for item in changed_items:
            lines.append(f"- {item}")

    try:
        requests.post(SLACK_WEBHOOK, json={"text": "\n".join(lines)}, timeout=10)
    except Exception as e:
        print(f"Slack 알림 실패: {e}")

def main():
    services = get_app_containers()
    changes = []

    for name, base_url in services.items():
        changed, is_new = check_swagger(name, base_url)
        if changed:
            changes.append((name, is_new))

    if changes:
        notify_slack(changes)
        print(f"변경 감지: {[c[0] for c in changes]}")
    else:
        print("변경 없음")

if __name__ == "__main__":
    main()
