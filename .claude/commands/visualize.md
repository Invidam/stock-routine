사용법: /visualize {월} — 차트만 재생성
- `{월}` (필수): 시각화할 월. YYYY-MM 형식 (예: 2026-01)

예시:
- `/visualize 2026-01` → 2026년 1월 차트 재생성

인자: $ARGUMENTS

인자에서 월(YYYY-MM)을 파싱해서 다음 명령어를 실행해:

```bash
PYTHONPATH=. .venv/bin/python -m visualization.visualize_portfolio --month {월}
```