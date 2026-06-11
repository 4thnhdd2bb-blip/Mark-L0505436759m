# METACOD — передача Омеру

Готовое к сборке приложение: **Expo React Native (TypeScript)** клиент + **Firebase**
(Cloud Functions + Firestore + Auth). Движок — общий чистый TS в `shared/engine`, поэтому
разбор работает и офлайн на устройстве врача, и как функция на Firebase.

> Это handover-спецификация монорепо Omer (`metacod-omer.zip` из архива проекта,
> см. `docs/project-archive-2026-06-11.md`). Сам код монорепо хранится в архиве у автора, а НЕ в этом
> git-репозитории. Источник истины для разборов-знаний — markdown в `docs/sources/`.

## Требования
- Node 20, npm
- Expo CLI (`npx expo`), Firebase CLI (`npm i -g firebase-tools`)
- Аккаунт Firebase (проект), в `.firebaserc` подставить projectId

## Установка
```
npm install                 # ставит workspaces (client + server)
```

## Запуск (разработка)
```
# 1) эмуляторы Firebase (functions/firestore/auth)
firebase emulators:start
# 2) клиент Expo
npm run client              # или: cd client && npx expo start
```
Клиент офлайн работает без эмуляторов: разбор берётся из `shared/engine`.
Эмуляторы нужны только для серверного пути (`reviewCaseFn` / `saveCaseFn`).

## Деплой
```
cd server && npm run build && cd ..
firebase deploy             # functions + firestore rules/indexes
```
Перед деплоем заполнить env клиента (`EXPO_PUBLIC_FB_*`) — см. `client/src/lib/firebase.ts`.

## Архитектура
- `shared/types` — контракт пакета случая (`metacod_case_v1`) + кодек кода.
- `shared/engine` — движок: `reviewCase()` = красные флаги + DDI + каркас + энергии-метки + Hard Stops.
- `client` — два режима в одном app: пациент (сбор и отправка) и врач (вставка/загрузка → разбор + справочник).
- `server` — `reviewCaseFn` (разбор, требует auth), `saveCaseFn` (сохранить случай в Firestore).

## Модель данных (Firestore)
```
doctors/{uid}/cases/{caseId}: { pkg, summary{redFlags,interactions}, savedAt }
```
Правила: только аутентифицированный врач к своим записям (`firestore.rules`).

## Что доделать на стороне разработки (намеренно оставлено)
1. **Авторизация:** сейчас анонимная (`ensureSignedIn`). Для PHI заменить на email/SSO.
2. **Compliance:** хранение PHI под GDPR/HIPAA — шифрование, регион, retention.
3. **Данные справочника:** наполнить `shared/engine/ddi.ts` и пороги из вашей базы
   (`drug_index.json`, `glp1_ddi_matrix.json`) — структура типов готова.
4. **Переводы:** `client/src/i18n/{en,he}.ts` — каркас; RU полный, EN/HE перевести.

## Граница проекта (важно)
Подбор препарата и доза — решение врача. Энергии — объясняющий слой (метки направления),
не генератор назначений. Энергетический подбор препарата как предписание, а также
Hamer/GNM и Revici в онкологическом ведении — **не включены**. Подробно:
`shared/engine/README_ENGINE.md`.
