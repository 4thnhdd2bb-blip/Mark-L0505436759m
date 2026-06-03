/**
 * Русский словарь — структурные ключи для Part 1. Клинические строки правил
 * добавляются вместе с rule_pack в Part 2; полный UI-текст — в Part 3.
 */
import type { Dictionary } from "../keys.js";

export const ru: Dictionary = {
  // Уровни триажа
  "triage.RED": "Неотложно",
  "triage.YELLOW": "Осторожно",
  "triage.GREEN": "Стабильно",
  // Диспозиции
  "disposition.er_now": "Немедленно обратитесь в приёмное отделение.",
  "disposition.hold_glp1_reassess": "Приостановите дозу GLP-1 и пересмотрите пероральные препараты.",
  "disposition.continue": "Стабильно — продолжайте текущий план под наблюдением.",
  // Оси риска
  "risk.underexposure": "Недостаточная экспозиция (снижение всасывания)",
  "risk.delayed_onset": "Отсроченное начало действия (сдвиг Tmax вправо)",
  "risk.overexposure": "Избыточная экспозиция (снижение клиренса)",
  "risk.free_fraction_misleading": "Обманчивый общий уровень (повышение свободной фракции)",
  // Названия анализов
  "lab.egfr": "СКФ (eGFR)",
  "lab.crp": "С-реактивный белок (СРБ)",
  "lab.tsh": "ТТГ",
  "lab.ferritin": "Ферритин",
  "lab.tsat": "Насыщение трансферрина",
  "lab.alt_ast": "АЛТ / АСТ",
  "lab.inr": "МНО",
  "lab.albumin": "Альбумин",
};
