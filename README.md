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
- **Part 2** — `rule_pack_v1.json`, `drug_master_v1.json`, рефактор Pharmacist Agent,
  Firestore-схема/migrations. *(нужны v4-файлы)*
- **Part 3** — Expo-RN UI (RTL/trilingual), PDF, тестовая стратегия, evidence rubric,
  roadmap.
