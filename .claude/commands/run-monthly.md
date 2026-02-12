사용법: /run-monthly {월} {매수기준일} — 월별 전체 파이프라인 실행
- `{월}` (필수): 분석할 월. YYYY-MM 형식 (예: 2026-01)
- `{매수기준일}` (선택): 주가 조회 기준일. 숫자 (예: 25). 생략 시 기본값 26

예시:
- `/run-monthly 2026-01 25` → 2026년 1월, 25일 주가 기준
- `/run-monthly 2026-02` → 2026년 2월, 26일 주가 기준 (기본값)

인자: $ARGUMENTS

인자에서 첫 번째 값은 월(YYYY-MM), 두 번째 값은 매수기준일(숫자)이야.

다음 명령어를 실행해:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_monthly.py --month {월} --yaml monthly/{월}.yaml --purchase-day {매수기준일}
```

매수기준일이 생략되면 `--purchase-day` 옵션 없이 실행해 (기본값 26 사용).
