사용법: /analyze {월} — 포트폴리오 분석만 실행
- `{월}` (필수): 분석할 월. YYYY-MM 형식 (예: 2026-01)

예시:
- `/analyze 2026-01` → 2026년 1월 포트폴리오 분석

인자: $ARGUMENTS

인자에서 월(YYYY-MM)을 파싱해서 다음 명령어를 실행해:

```bash
PYTHONPATH=. .venv/bin/python -m core.analyze_portfolio --month {월} --overwrite
```