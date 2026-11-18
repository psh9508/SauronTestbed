# Sauron Testbed

[Sauron](../Sauron) 에러 분석 서버를 end-to-end로 테스트하기 위한 샘플 프로젝트.

- `shop/` — 의도적인 버그가 심어진 샘플 쇼핑 앱 (Sauron이 소스를 읽어갈 대상)
- `commerce/` — 주문/결제/재고/알림 흐름을 가진 샘플 앱 (고난도 시나리오용)
- `sauron_reporter/` — sentry-sdk를 Sauron DSN으로 초기화하고, 전송한 에러의 분석 job을 찾아 폴링하는 클라이언트
- `scenarios.py` — 버그 재현 시나리오
- `run_scenarios.py` — 시나리오 실행 → Sauron 전송 → 분석 결과 출력
- `smoke_api.py` — LLM과 무관한 API 동작 검증 (Sentry 수집, 에러 코드, fingerprint 중복 처리)
- `register_repo.py` — 코드 저장소 등록 / 목록 조회

## 준비

1. Sauron 서버 실행 (Sauron 프로젝트에서)
   ```bash
   docker compose --env-file .env -f dependency/docker-compose.yml up -d
   uv run uvicorn main:app --host 127.0.0.1 --port 8002
   ```
2. 이 디렉터리를 GitHub 또는 GitLab 저장소로 push
   Sauron agent는 stacktrace의 경로(`shop/orders.py` 등)를 저장소 트리와 매칭해 소스를 읽어온다.
3. 저장소 등록 후 발급된 `public_key`를 `.env`에 설정
   ```bash
   cp .env.example .env
   uv run python register_repo.py github --repo owner/sauron-testbed \
       --app-id <APP_ID> --installation-id <INSTALLATION_ID> --pem app.pem
   # 또는
   uv run python register_repo.py gitlab --base-url https://gitlab.example.com --token glpat-xxx
   ```
   GitLab이면 `.env`의 `SAURON_REPOSITORY_URL`에 저장소 URL도 넣는다.

## 실행

```bash
uv run python smoke_api.py              # API 스모크 테스트 (key 없으면 일부 건너뜀)
uv run python smoke_api.py --wait       # 생성한 job 완료까지 확인

uv run python run_scenarios.py --list
uv run python run_scenarios.py --dry-run missing_address   # 전송 없이 sentry 이벤트 확인
uv run python run_scenarios.py                             # 전체 실행 + 결과 대기
uv run python run_scenarios.py zero_stock --no-wait
```

에러는 sentry-sdk가 `http://<SAURON_REPOSITORY_KEY>@<host>/1` DSN으로 Sauron에 보낸다.
Sentry 엔드포인트는 job_id를 돌려주지 않으므로, 전송 전후의 `GET /analyze/errors`를 비교해 이번 전송의 이벤트와 job을 찾는다 (시나리오는 하나씩 순서대로 보낸다).

같은 시나리오를 다시 보내면 fingerprint가 같으므로 새 job 대신 기존 job이 쓰이고 `event_count`만 늘어난다.

`GIT_COMMIT_SHA` 환경변수(또는 `.env`)를 설정하면 sentry `release`와 `git_commit_sha` 태그로 실려 Sauron이 그 커밋 기준으로 소스를 읽는다.

```bash
GIT_COMMIT_SHA=$(git rev-parse HEAD) uv run python run_scenarios.py string_price
```

## 시나리오

| 이름 | 에러 | 심어둔 버그 |
|---|---|---|
| `unknown_product` | KeyError | `catalog.get_product`가 없는 상품 ID 처리 안 함 |
| `zero_stock` | ZeroDivisionError | `catalog.stock_ratio`에서 재고 0 나눗셈 |
| `string_price` | TypeError | `PRODUCTS["P-300"]` 가격이 문자열 → 쿠폰 계산에서 터짐 (원인과 발생 지점이 다름) |
| `invalid_coupon` | TypeError | `pricing.apply_coupon`이 없는 쿠폰(None) 처리 안 함 |
| `broken_coupon` | KeyError | `COUPONS["BROKEN"]`에 `value` 누락 |
| `missing_address` | TypeError | 주소 없는 유저 → `orders` → `users` 깊은 호출에서 발생 |
| `bad_quantity` | ValueError | `orders.place_order`가 quantity 검증 없이 `int()` |
| `missing_email` | AttributeError | 이메일 None 유저의 `email_domain` |
| `payment_timeout` | (message) | stacktrace 없는 message 이벤트 (ERROR 로그로 전송) |

### 고난도 시나리오 (`commerce/`)


| 이름 | 흐름 |
|---|---|
| `preview_then_checkout` | VIP 회원이 견적을 확인한 뒤 같은 장바구니로 결제 |
| `team_keyboard_order` | Gold 회원의 키보드 대량 주문 |
| `desk_setup_order` | Silver 회원의 키보드 + 마우스 주문 |
| `installment_checkout` | 12개월 할부 결제 등록 |
| `restock_broadcast` | 두 상품의 재입고 알림 연속 발송 |
| `streaming_bundle_price` | 스트리밍 번들 가격 조회 |
