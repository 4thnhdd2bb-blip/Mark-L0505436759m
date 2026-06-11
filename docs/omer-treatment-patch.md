# METACOD — патч лечения для монорепо Omer (наложение, НЕ новая версия)

Накладывается на существующий `metacod-omer` (Expo RN + Firebase) **без смены архитектуры**.
Только добавляет: данные + модуль отёчного слоя (Layer 0) + справочную схему лечения цзюнь-чэнь-цзо-ши.
Существующий `reviewCase()` (красные флаги + DDI + каркас + Hard Stops) **не переписывается** — в него добавляются два вызова.

> Это спецификация патча для монорепо Omer (см. `docs/omer-handover.md`, `docs/project-archive-2026-06-11.md`).
> Сам код патча (`patch_for_omer/`) хранится в архиве у автора, а НЕ в этом git-репозитории.

## 1. Копирование (поверх, обратносовместимо)
Скопировать содержимое `patch_for_omer/` в корень репо:
```
shared/data/treatment_database_350.json   # заменить существующий (та же схема ключей, добавлены поля)
shared/data/drug_safety_kcts.json         # новый
shared/data/data_fixes_applied.json       # лог 44 исправлений кодов (для справочника)
shared/engine/metacod_treatment_types.ts  # типы модуля лечения (НЕ конфликтует с shared/types)
shared/engine/energies.ts
shared/engine/diagnosis.ts
shared/engine/edemaLayer.ts               # Layer 0 (KCTS/PWRS), research-modifier
shared/engine/treatment.ts                # цзюнь-чэнь-цзо-ши + сверка
shared/engine/metacodTreatment.ts         # ТОЧКА ВХОДА: buildTreatment / screenEdema / edemaDrugWarnings
```
Новые поля в `treatment_database_350.json`: в препаратах `energy_profile.opposite_suppresses_canonical` + `energy_scope`; в болезнях `staged_pair`, `edema_layer_relevant`. Старые поля не тронуты.

## 2. Встраивание в существующий `reviewCase()` (2 вставки)
В `shared/engine/reviewCase.ts` (или где у вас `reviewCase`), не меняя текущую логику:

```ts
import { buildTreatment, screenEdema, edemaDrugWarnings } from './metacodTreatment';

export function reviewCase(pkg /* metacod_case_v1 */) {
  // ... существующее: redFlags, DDI, каркас, energy-метки, Hard Stops ...

  // (A) Layer 0 — скрин отёчного слоя (research-modifier)
  const edema = screenEdema({
    attendedAlone:           pkg?.context?.attendedAlone ?? false,
    chronicRefractoryOver5y: pkg?.context?.chronicOver5y ?? false,
    isolationInMajorEvents:  pkg?.context?.isolation ?? false,
    soleCarrierResponsibility: pkg?.context?.soleCarrier ?? false,
    multipleParallelChronic: (pkg?.diagnoses?.length ?? 0) >= 3,
    risingWeightFaceLegs:    pkg?.context?.risingWeight ?? false,
  });
  const edemaWarnings = edemaDrugWarnings(pkg?.medications ?? [], edema.suspected);

  // (B) Справочная схема лечения по основному диагнозу (если есть icd/имя)
  const dx = pkg?.diagnoses?.[0];
  const treatment = dx ? buildTreatment({ icd10: dx.icd10, name_ru: dx.name_ru }) : null;

  return {
    ...existingSummary,           // redFlags, interactions, frame, energyTags, hardStops
    edema,                        // { suspected, positiveMarkers, recommendBiomarkers, vector }
    edemaWarnings,                // [{ name, warnings[] }] — показывать при активном слое
    treatment,                    // { diagnosis{protocol,regime,stagedPair,...}, scheme[jun/chen/zuo/shi], verification }
  };
}
```

Серверный путь (`reviewCaseFn`) и офлайн на клиенте получают `treatment`/`edema` автоматически — модуль чистый TS, без побочных зависимостей.

## 3. Контракт случая (metacod_case_v1)
Используются опциональные поля; если их нет — модуль деградирует мягко (edema = 0 маркёров, treatment = null):
- `pkg.diagnoses: [{ icd10?, name_ru? }]`
- `pkg.medications: [{ id?, name_ru? }]`
- `pkg.context: { attendedAlone?, chronicOver5y?, isolation?, soleCarrier?, risingWeight? }` (для Layer 0)

## 4. Граница проекта (соблюдена как у вас)
- Энергии — **объясняющий слой**, не генератор назначений. Схема цзюнь-чэнь-цзо-ши — **справочный разбор**, не предписание.
- Отёчный слой (KCTS/PWRS) — **research-modifier**, помечен как таковой; не заменяет нефро/эндо/психиатрию.
- Hamer/GNM, Revici в онкологии, энергетический подбор как предписание — **НЕ включены**.
- Решение, выбор препарата и доза — за лечащим врачом.

## 5. Что внутри данных уже исправлено
44 коллизии кодов лечения (номер≠суффикс) исправлены: напр. Wegener → Государь **Ритуксимаб/Циклофосфамид** (было Метилфенидат/Лоразепам). Полный лог — `shared/data/data_fixes_applied.json`.

## Проверка
Модуль `shared/engine/*` компилируется автономно (`tsc --noEmit`, strict) и покрыт 4 тестами в справочной сборке. После наложения — `npm run build` сервера и `npx expo start` клиента как обычно.
