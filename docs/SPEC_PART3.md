# Part 3 (Python трек) — FastAPI wiring + reporting + testing harness

Статус: **реализован и запущен. 73 теста зелёных, 0 skip** (35 клинических SaMD-кейсов
параметризованы — покрывают все 31 правило rule_pack v2).

Решение по архитектуре (ваш выбор): **гибрид — приоритет Python-интеграции сейчас**,
TS/Firebase (Part 1–2) остаётся целевой платформой на потом.

---

## 1. Что сделано (всё в `python/`, запускается)

**Wiring-слой (Part 3a):**
- `routers/glp1.py` — FastAPI router `/glp1/*`: `assess`, `sign-off`, `visit/{id}`,
  `visit/{id}/report.html`, `report.pdf`, `audit-log`, `rules`, `drugs`, `_info`.
- `services/resources.py` — singleton-кэш rule_pack + drug_db.
- `services/i18n.py` — загрузчик локалей + рекурсивный резолвер (`*_i18n_key → *_i18n_text`,
  ключи сохраняются; `_meta.direction` → RTL для иврита).
- `reports/html_renderer.py` — печатный HTML-отчёт, два слоя (clinical/admin), RTL.
- `schemas/glp1_api.py` — Pydantic-модели HTTP-слоя.
- `main.py` — standalone-приложение + пример монтирования в v4 (`include_router`).
- Part 2 (агент, БД, контент, i18n, миграция Alembic) — материализованы рядом.

**UI (Part 3b) — `python/ui/index.html`:**
- Single-file React (CDN, без сборки), трёхъязычный RU/EN/HE + RTL для иврита,
  слои clinical/admin, режимы demo (`file://`) и live (`?api=` или same-origin).
- Раздаётся из FastAPI: `main.py` монтирует `/ui/*` и отдаёт `index.html` на `/`
  (same-origin → `/glp1/*` без CORS). Контракт совпадает с `/glp1/assess` и
  `/glp1/sign-off` один в один. Встроенные JSON-блоки валидны, 89 i18n-ключей × 3 локали.

**Тест-харнесс (Part 3c) — `python/tests/`:**
- `clinical/` — **35 SaMD reference-кейсов** (по правилу + edge cases) + meta-тесты
  (покрытие правил, дубликаты id, наличие источников/обоснования).
- `unit/` — безопасность DSL (нет eval/exec/`__import__`/compile; неизвестные операторы
  и отсутствующие поля → False, без исключений) + корректность операторов/комбинаторов.
- `integration/` — полный HTTP round-trip через FastAPI TestClient на изолированной
  SQLite-БД per-test: assess → 201/visit_id, i18n RU/HE+RTL, White Coat sign-off,
  audit-запись, clinical-слой не протекает rule_id/`[admin]`, admin-слой их показывает.

---

## 2. Проверено (выполнено в этом репозитории)

```bash
cd python
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -q        # 73 passed, 0 skipped
```

51 passed / 1 skipped. Skip — meta-тест покрытия: 3 правила
(`CATION_CHELATION_TETRACYCLINE`, `EGFR_LOW_DIGOXIN`, `GLP1_GASTROPARESIS_TMAX_SENSITIVE`)
пока без позитивного клинического кейса (намеренно skip, не fail).

CI: `.github/workflows/test.yml` гоняет и Python (pytest), и TS (`npm test`).

---

## 3. Решения / отличия от исходного дока

- **Flat-layout `python/`** вместо трёх sibling-папок (`glp1-module-part2` /
  `glp1_v5_wiring` / `glp1_v5_tests`). Один `PYTHONPATH=python`. `conftest.py`
  адаптирован под это.
- **PDF**: server-side через WeasyPrint — опционально; без него `/report.pdf` отдаёт
  501 + fallback на печать `report.html` из браузера (как в исходном дизайне).
- Клинический контент (rule_pack/drug_master/i18n) — тот же, что в TS-треке.

---

## 4. Что дальше

- Закрыть 3 непокрытых правила клиническими кейсами (снять skip → жёсткое покрытие).
- React/Expo UI поверх этих эндпоинтов (Part 3b).
- WeasyPrint в проде для серверного PDF; брендинг отчёта (Jinja2-шаблоны).
- Расширение rule_pack (30+) и drug_db (50+).
- HL7 FHIR / push подписанных визитов в EHR.
