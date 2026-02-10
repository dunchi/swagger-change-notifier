# swagger-change-notifier

MSA 환경에서 Docker 컨테이너의 Swagger(OpenAPI) 스펙 변경을 자동 감지하고 Slack으로 알림을 보내는 도구.

## 요구사항

- Python 3.x
- Docker
- requests 라이브러리 (`pip install requests`)

## 설치

### 1. 스크립트 복사

```bash
mkdir -p ~/scripts/swagger-specs
cp swagger-monitor.py ~/scripts/
chmod +x ~/scripts/swagger-monitor.py
```

### 2. 설정 수정

`swagger-monitor.py` 파일에서 다음 값을 수정:

```python
SLACK_WEBHOOK = "YOUR_SLACK_WEBHOOK_URL"  # Slack Incoming Webhook URL
SPEC_STORE = os.path.expanduser("~/scripts/swagger-specs")  # 해시 저장 경로
EXCLUDE_APPS = ["keycloak-app", "config-app"]  # 제외할 컨테이너
```

### 3. Cron 등록

```bash
crontab -e
```

5분마다 실행:
```
*/5 * * * * /usr/bin/python3 /home/user/scripts/swagger-monitor.py >> /home/user/scripts/swagger-monitor.log 2>&1
```

## 동작 방식

1. `docker ps`에서 `*-app` 패턴의 컨테이너 자동 탐지
2. 각 컨테이너의 `/v3/api-docs` 엔드포인트에서 OpenAPI 스펙 조회
3. MD5 해시로 이전 스펙과 비교
4. 변경 감지 시 Slack으로 알림 전송

### 포트 탐지 규칙

- `80xx`, `81xx`, `70xx`, `60xx` 포트를 API 포트로 인식
- `5xxx` 포트는 디버그 포트로 간주하여 제외

## Slack 알림 예시

```
*스웨거 스펙 알림* (2026-02-10 17:30)

신규
- ums
- notification

변경
- core
- approval
```

## 수동 실행

```bash
python3 ~/scripts/swagger-monitor.py
```

### 해시 초기화 (전체 재탐지)

```bash
rm -f ~/scripts/swagger-specs/*.hash
python3 ~/scripts/swagger-monitor.py
```

## 로그 확인

```bash
tail -f ~/scripts/swagger-monitor.log
```
