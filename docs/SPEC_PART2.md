# Part 2 — Порт клинического ядра v4 → v5 (TS/Firebase)

Статус: **реализован, typecheck + тесты зелёные (5/5), паритет с v4 demo подтверждён.**

Part 2 переносит валидированное клиническое ядро v4 (Pharmacist Agent, rule_pack,
drug_master, i18n, модель данных) в архитектуру v5 на TypeScript/Firebase из Part 1.

---

## 1. Что портировано (1:1)

| v4 (Python/Pydantic) | v5 (TypeScript/zod) |
|---|---|
| `pharmacist_agent.py` → `PharmacistAgent` | `packages/engine/src/pharmacistAgent.ts` |
| `RuleEvaluator` (DSL `and/or/not` + `field`) | `packages/engine/src/evaluator.ts` |
| `rule_pack_v1.json` (15 правил) | `packages/engine/content/rule_pack_v1.json` (verbatim) |
| `drug_master_v1.json` (21 профиль) | `packages/engine/content/drug_master_v1.json` (verbatim) |
| `i18n ru/en/he` (полные строки) | `packages/shared/src/i18n/locales/{ru,en,he}.ts` |
| Pydantic-модели вход/выход | `packages/shared/src/schemas/*` (zod) |
| `database.py` (SQLAlchemy) | `packages/shared/src/schemas/persistence.ts` + Firestore (`functions`) |

Пороги триажа, DOSE HOLD-логика, future risks и chronic adjustments перенесены
с теми же константами (`THRESHOLDS` в `pharmacistAgent.ts`).

---

## 2. Ключевые архитектурные решения

1. **Контент — source of truth, взят дословно.** `rule_pack_v1.json` и
   `drug_master_v1.json` лежат как JSON (клиническая команда правит данные, не код),
   version-pinned с деплоем, валидируются zod-схемами при загрузке
   (`packages/engine/src/content.ts`, `loadContent()`).
2. **Схемы Part 1 приведены к формату v4** (DSL `field`-пути в контекст
   `{patient, drug}`, 4 оси риска как поля finding, `admin_layer`). Это сохранило
   ваш валидированный контент без переписывания.
3. **Движок — чистая логика без I/O** (`@metacod/engine`): `assess()` детерминирован,
   одинаково работает на сервере (Functions) и для предпросмотра.
4. **Персистентность — Firestore** (вы выбрали Firebase). Концепции SQLAlchemy-модели
   перенесены: один **Visit** = снапшот input+output с version-pin + `medication_snapshots`
   + `rule_triggers` + `sign_off`; отдельный **audit_log** (append-only). SQLAlchemy/Alembic
   из v4 — это прототип; реляционный эквивалент при необходимости (Cloud SQL) возможен
   без изменения движка.

---

## 3. Серверный API (Firebase callable)

`functions/src/api.ts` (чистые хендлеры) + `index.ts` (Firestore-привязка):

| Функция | White Coat / authz |
|---|---|
| `assessPatient({ input })` | Запускает агента, сохраняет Visit (`pending_sign_off`), пишет audit, возвращает проекцию по роли |
| `signOffAssessment({ visit_id, decision: sign/reject/amend, notes? })` | Только `physician`; только из `pending_sign_off`; audit |
| `getReport({ visit_id, locale, view })` | `view: patient` требует `signed`; admin/research — соответствующей роли |

---

## 4. Dual-layer проекция (`projection.ts`)

- **admin / research** — всё, включая `admin_trace` (внутренняя терминология паттернов).
- **physician** — клинический контент + `rule_id` + механизм; внутренняя терминология
  паттернов скрыта.
- **patient** — только триаж, пациентские действия и решение по дозе GLP-1; НИКОГДА
  rule_id, механизмы, паттерны, оси риска, врачебные действия, лаб-план, forecast.

---

## 5. Паритет с v4 (тест `packages/engine/test/parity.mjs`)

Reference-пациент **P-DEMO-001** (58 ж, тирзепатид 2 нед, ИПП, LT4-таблетка, апиксабан,
омепразол; nausea 7, vomiting 1, eGFR 52, TSH 6.4):
- триаж → **YELLOW**; GLP-1 → **HOLD**;
- сработало **1** правило: `LT4_TABLET_PPI` (underexposure high), traceable по rule_id;
- future risks → `aki_dehydration` + `lt4_drift_ppi`; chronic adjustments → нет;
- `sign_off_status` → `pending_sign_off` (White Coat).
- контент: 15 правил, 21 профиль — валидируются.
- dual-layer инварианты (strip для physician/patient) — проверены.

---

## 6. Что дальше (Part 3)

- Expo-RN UI (RTL/trilingual, styles в отдельных файлах), рендер i18n-ключей.
- Генерация PDF-отчёта (clinician + patient layers).
- Firestore security rules (field-level) + admin-приложение управления контентом.
- Evidence grading rubric (A/B/C) как документ.
- Расширение drug_master/rule_pack, тестовая матрица клинических кейсов.
