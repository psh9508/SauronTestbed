# Sauron Testbed

[Sauron](../Sauron) 에러 분석 서버를 end-to-end로 테스트하기 위한 샘플 프로젝트.

- `shop/` — 의도적인 버그가 심어진 샘플 쇼핑 앱 (Sauron이 소스를 읽어갈 대상)
- `sauron_reporter/` — 표준 라이브러리만 쓰는 최소 Sauron 클라이언트 (예외 → `POST /analyze`, job 폴링, 로그 breadcrumbs 수집)
- `scenarios.py` — 버그 재현 시나리오
- `run_scenarios.py` — 시나리오 실행 → Sauron 전송 → 분석 결과 출력
- `smoke_api.py` — LLM과 무관한 API 동작 검증 (validation, 에러 코드, fingerprint 중복 처리)
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
uv run python run_scenarios.py --dry-run missing_address   # 전송 없이 payload 확인
uv run python run_scenarios.py                             # 전체 실행 + 결과 대기
uv run python run_scenarios.py zero_stock --no-wait
```

같은 시나리오를 다시 보내면 fingerprint가 같으므로 새 job 대신 기존 job과 증가된 `event_count`가 돌아온다.

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
| `payment_timeout` | (message) | stacktrace 없는 message 이벤트 |
