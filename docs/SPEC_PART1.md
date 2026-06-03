# METACOD — GLP-1 Complication Prevention (v5)
## Part 1 — Scope, Architecture, Data Schemas, API surface, METACOD integration

Статус: **Part 1 реализован и проходит typecheck + smoke-тесты**.
Стек зафиксирован: **TypeScript + Expo-React-Native (клиент) / Firebase (сервер)**.

---

### 1. Scope

Модуль — clinical decision support для пациентов на GLP-1/GIP-терапии
(семаглутид — Ozempic/Wegovy; тирзепатид — Mounjaro/Zepbound; и др.), одновременно
принимающих **пероральные** препараты.

Ключевой принцип — **рассуждение через механизм, не «болезнь X → доза −25 %»**:

> GLP-1 → ↓ опорожнение желудка → отсроченный Tmax / вариабельный Cmax →
> ненадёжная пероральная терапия.

Эта ненадёжность раскладывается на **4 независимых риска** (`RiskType`):

| Ось | Механизм |
|---|---|
| `underexposure` | ↓ биодоступность (F↓) → субтерапевтично |
| `delayed_onset` | сдвиг Tmax вправо → эффект приходит поздно/непредсказуемо |
| `overexposure` | ↓ клиренс (печёночный/почечный) → накопление → токсичность |
| `free_fraction_misleading` | низкий альбумин → ↑ свободная фракция (общий уровень обманчив) |

Part 1 поставляет фундамент (схемы + движок + API), **без** наполнения rule_pack и
drug_master — это Part 2.

---

### 2. Architecture

Монорепо (npm workspaces). Аккуратное разделение клиент/сервер; вся клиническая
логика — в чистом TS-пакете, который **одинаково** работает на сервере и (для
предпросмотра) на клиенте.

```
packages/
  shared/     @metacod/shared   — zod-схемы + i18n (RU/EN/HE). Импортируют ОБА: клиент и сервер.
  engine/     @metacod/engine   — чистая клиническая логика: триаж, rule engine,
                                  Pharmacist Agent, dual-layer проекция. Без I/O.
functions/    @metacod/functions — Firebase Cloud Functions: транспорт + Firestore
                                  вокруг engine (assessPatient / signOffAssessment / getReport).
apps/
  mobile/     Expo-React-Native клиент (каркас — Part 3; styles в отдельных файлах).
firebase.json, firestore.rules, firestore.indexes.json
```

Почему так:
- **Движок без I/O** (чистые функции, все id/время/версии инжектируются) →
  детерминирован, тестируем, переносим между Firebase и клиентом.
- **Firebase = только транспорт + персистентность** (порты в `functions/src/ports.ts`).
- Схемы на **zod** заменяют Pydantic из v4: одно определение даёт и runtime-валидацию
  на сервере, и статические типы на клиенте через `z.infer`.

---

### 3. Data Schemas (zod ← бывш. Pydantic)

Все в `packages/shared/src/schemas`:

| Файл | Что описывает |
|---|---|
| `common.ts` | `EvidenceGrade` (A/B/C), `Locale`, `Severity`, `Source`, `LocalizedText` (i18n-ключ + params) |
| `patient.ts` | `PatientInput`: GLP-1-терапия (агент/фаза/недели), `MedicationEntry`, `Labs`, `Conditions`, `Symptoms` |
| `drug.ts` | **Drug Profile Schema** — молекулярный профиль (см. §4) |
| `rule.ts` | `Rule` + `RulePack`: декларативный `Condition` AST, evidence, sources, mechanism_trace |
| `risk.ts` | `RiskType` (4 оси), `RiskFlag` (с rule_id + mechanism_trace) |
| `triage.ts` | `TriageLevel` (RED/YELLOW/GREEN), `TriageResult` |
| `audit.ts` | `SignOffState` (White Coat Rule), `SignOffRecord`, `AuditLogEntry`, `UserRole` |
| `engineOutput.ts` | `EngineOutput`, `PharmacistForecast`, `ViewLayer`, `ActionItem`, `LabOrder` |

Главный инвариант: **ни одна user-facing строка не является литералом** — везде
`LocalizedText { key, params }`, резолвится на краю (клиент/PDF) по локали.

---

### 4. Drug Profile Schema (молекулярный)

Правила НЕ хардкодят названия. Правило спрашивает «препарат gastric-emptying-
sensitive И chelation-sensitive?», ответы берутся из профиля. Это держит rule_pack
маленьким и даёт новым препаратам наследовать правила простым заполнением свойств.

`DrugProfile` группирует: `absorption` (биодоступность, чувствительность к опорожнению
желудка, Tmax, кислотозависимость), `distribution` (first-pass, hepatic extraction,
protein binding, albumin-bound), `metabolism` (CYP substrate/inhibitor/inducer),
`elimination` (renal/hepatic fraction, t½), `properties` (NTI, modified_release,
chelation_sensitive, polyvalent_cation_source, doac/vka), `forms_available`,
`routes_available`, `sources`.

`drug_master_v1.json` (Part 2) — массив объектов, валидируемых `DrugProfile`.

---

### 5. Rule schema + движок

`Rule.when` — декларативный `Condition` AST (`all`/`any`/`not` + листовые предикаты:
`patient` (dot-path + оператор), `glp1_agent` (+окно недель), `has_medication`,
`concurrent` (+`within_hours` для разнесения катионов). Это делает rule_pack **данными,
а не кодом** — версионируется, аудируется, (позже) ревьюится врачами без деплоя.

Каждое правило несёт: `rule_id`, `evidence_grade` A/B/C, `sources`, `mechanism_trace`
(i18n, admin/clinical), `internal_pattern_name` (admin-only), `clinician_actions`,
`patient_actions`, `lab_plan`.

Реализовано и протестировано в `packages/engine`:
- `evaluator.ts` — оценщик `Condition` AST (ядро; rule_pack = чистые данные);
- `triage.ts` — RED/YELLOW/GREEN по порогам спецификации;
- `ruleEngine.ts` — прогон rule_pack → risk_flags/actions/lab_plan (каждое с rule_id);
- `pharmacistAgent.ts` — **baseline** DOSE HOLD (полный рефактор — Part 2);
- `projection.ts` — dual-layer проекция;
- `assess.ts` — оркестратор: триаж → правила → pharmacist → `EngineOutput`
  (старт в состоянии `pending_sign_off`).

---

### 6. API surface (Firebase callable)

`functions/src/api.ts` — чистые хендлеры; `index.ts` — привязка к Firebase + Firestore.

| Функция | Вход | Выход | Примечание |
|---|---|---|---|
| `assessPatient` | `{ input: PatientInput }` | `{ assessment_id, view, output }` | Сохраняет полный (admin) output, пишет audit `assess`, возвращает проекцию по роли |
| `signOffAssessment` | `{ assessment_id, decision: sign\|reject, method, rejection_reason? }` | `{ assessment_id, sign_off }` | **White Coat Rule**: только `physician`, только из `pending_sign_off` |
| `getReport` | `{ assessment_id, locale, view }` | `{ assessment_id, locale, view, output }` | `view: patient` требует `signed`; admin/research — соответствующей роли |

Authz и проекция — по custom-claim `role` пользователя.

---

### 7. METACOD integration requirements

- **Trilingual (RU/EN/HE + RTL):** `packages/shared/src/i18n`. `isRtl('he') === true`,
  `direction()` для RN-стилей. Всё через ключи; полный клинический текст — с rule_pack
  (Part 2) и UI (Part 3).
- **White Coat Rule:** `pending_sign_off → signed → EHR`; экспорт пациентского отчёта
  возможен ТОЛЬКО из `signed`. Машина состояний в `audit.ts`, enforcement в `api.ts`.
- **Audit:** неизменяемый `AuditLogEntry` — версия rule_pack + drug_master, user, role,
  timestamp, sha-256 хеши input/output снапшотов. Append-only коллекция, server-only.
- **Dual-layer:** один полный `EngineOutput`, проекции `admin`/`research`/`physician`/
  `patient`. Инвариант: пациент НИКОГДА не видит rule_id, mechanism_trace, internal
  pattern names, оси риска, врачебные действия, lab orders. Internal pattern names —
  только admin/research.
- **SaMD Class IIa:** rule versioning, evidence sources на каждом правиле, полная
  traceability (rule_id во всех выводах), audit logging — заложены в схемы.

---

### 8. Проверка (выполнено)

```
npm install
npm run build      # tsc -b shared + engine + functions → EXIT 0
npm test           # build + node --test → 5/5 pass
```

Smoke-тест (`packages/engine/test/smoke.mjs`) покрывает: срабатывание правила PPI+LT4 с
traceable rule_id, RED-short-circuit, YELLOW при эскалации GLP-1 <4 нед, dual-layer
проекцию (strip для пациента/врача/админа), прямой матч свойств препарата.

---

### 9. Что дальше

- **Part 2:** `rule_pack_v1.json` (15–20 правил из приоритетного списка), `drug_master_v1.json`
  (~30 профилей), рефактор Pharmacist Agent (DOSE HOLD, future risks, chronic med
  adjustments) с i18n + evidence grading, Firestore-схема/seed/security rules.
  **Нужны ваши v4-файлы** (codebase, `drug_master_starter.json`, PK reference, sample cases) —
  вставьте в чат.
- **Part 3:** Expo-RN UI (RTL/trilingual, styles в отдельных файлах), генерация PDF,
  тестовая стратегия, evidence grading rubric (A/B/C), phased roadmap.
