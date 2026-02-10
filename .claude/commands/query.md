사용법: /query {월|--list} — DB 데이터 조회
- `{월}` (선택): 조회할 월. YYYY-MM 형식 (예: 2026-01)
- `--list` (선택): 저장된 월 목록 조회
- 인자 없으면 `--list`로 동작

예시:
- `/query 2026-01` → 2026년 1월 데이터 조회
- `/query --list` → 저장된 월 목록 조회
- `/query` → 저장된 월 목록 조회

인자: $ARGUMENTS

인자가 `--list`이면 저장된 월 목록을 조회하고, YYYY-MM 형식의 월이면 해당 월 데이터를 조회해.

다음 명령어를 실행해:

- 월 목록 조회: `PYTHONPATH=. .venv/bin/python -m data.query_db --list`
- 특정 월 조회: `PYTHONPATH=. .venv/bin/python -m data.query_db --month {월}`

인자가 비어있으면 `--list`로 실행해.