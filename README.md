# METACOD — GLP-1 Complication Prevention (v5)

Clinical decision support для пациентов на GLP-1/GIP-терапии (семаглутид —
Ozempic/Wegovy; тирзепатид — Mounjaro/Zepbound), одновременно принимающих
пероральные препараты. Часть платформы **METACOD Health**.

> **Стек:** TypeScript · Expo-React-Native (клиент) · Firebase (сервер).
> Клиническая логика — в чистом TS-пакете, одинаково работающем на сервере и клиенте.

## Структура (монорепо)

```
packages/shared      @metacod/shared    zod-схемы + i18n (RU/EN/HE, RTL)
packages/engine      @metacod/engine    триаж · rule engine · Pharmacist Agent · dual-layer
functions            @metacod/functions Firebase Cloud Functions (API surface)
apps/mobile          Expo-RN клиент (Part 3)
docs/SPEC_PART1.md   спецификация Part 1
```

## Быстрый старт

```bash
npm install
npm run build     # typecheck + сборка shared + engine + functions
npm test          # build + node --test (smoke-тесты движка)
```

## Принцип

Рассуждение через **механизм**, не «болезнь X → доза −25 %»:
GLP-1 → ↓ опорожнение желудка → отсроченный Tmax / вариабельный Cmax →
ненадёжная пероральная терапия → 4 оси риска (underexposure / delayed onset /
overexposure / free fraction misleading).

## Статус

- **Part 1 ✅** — Scope, Architecture, Data Schemas, Drug Profile Schema, API surface,
  METACOD-интеграция (trilingual, White Coat Rule, audit, dual-layer). См.
  [`docs/SPEC_PART1.md`](docs/SPEC_PART1.md).
- **Part 2 ✅** — порт клинического ядра v4 → TS: Pharmacist Agent (v2.1, `med_summary`),
  `rule_pack_v2` (31 правило), `drug_master_v2` (60 профилей), полные i18n RU/EN/HE, Firestore-модель
  (Visit/RuleTrigger/SignOff/AuditLog), серверный API. Паритет с v4 demo подтверждён
  (5/5 тестов). См. [`docs/SPEC_PART2.md`](docs/SPEC_PART2.md).
- **Part 3a/3b/3c ✅ (Python, приоритетный трек)** — рабочая FastAPI-интеграция поверх v4:
  router `/glp1/*` (assess, sign-off, visit, report.html, audit-log, rules, drugs),
  серверный i18n-резолвер, HTML-отчёт (clinical/admin, RTL), SQLAlchemy-персистентность,
  **single-file React UI** (RU/EN/HE + RTL, clinical/admin, demo+live; раздаётся из
  FastAPI на `/`), Pharmacist Agent **v3.0** (DoseIndividualization / InteractionMatrix /
  BayesianLabProjector / Pharmacogenomics), **HL7 FHIR R4 экспорт** (`/glp1/visit/{id}/fhir-bundle`,
  детерминированный Bundle), **active learning** (захват врачебных правок при sign-off +
  аналитика паттернов `/glp1/learning/patterns`), **METACOD TCM-мост** (adapter:
  rule_id → energy/quantity axes → three-layer output patient/physician/hidden_admin;
  baseline-маппинг 31 правила, pending Mark's review), **Patient-Facing Filter**
  (детектор утечки proprietary/internal-терминологии в пациентский слой —
  Memory Rule #10 / §6.5), и тест-харнесс (**235 тестов, 0 skip**:
  60 клинических SaMD-кейсов + 24 v3-subsystem + 24 metacod-bridge +
  34 patient-facing-filter + unit DSL + i18n-покрытие + integration HTTP + UI).
  Всё в [`python/`](python/README_INTEGRATION.md).
- **Part 3 (TS, позже)** — Expo-RN UI (RTL/trilingual), PDF, security rules,
  evidence rubric, расширение rule_pack/drug_db.

## Два трека (гибрид)

| Трек | Где | Статус |
|---|---|---|
| **Python FastAPI** (приоритет сейчас, для интеграции с v4 / Oleg) | [`python/`](python/) | ✅ рабочий, 51 тест зелёный |
| **TS / Expo-React-Native / Firebase** (целевая платформа) | `packages/`, `functions/` | ✅ Part 1–2 (движок + API), UI позже |

Клиническое ядро (rule_pack, drug_master, i18n) **идентично** в обоих треках.
