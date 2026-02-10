n사용법: /evaluate [--detailed] — 적립식 투자 평가
- `--detailed` (선택): 종목별 상세 리포트 출력

예시:
- `/evaluate` → 기본 리포트
- `/evaluate --detailed` → 상세 리포트

인자: $ARGUMENTS

다음 명령어를 실행해:

```bash
PYTHONPATH=. .venv/bin/python -m core.evaluate_accumulative $ARGUMENTS
```

인자가 비어있으면 기본 리포트를 출력하고, `--detailed`가 포함되어 있으면 상세 리포트를 출력해.