/**
 * מילון עברית — מפתחות מבניים ל-Part 1. עברית נטענת RTL (ראו isRtl).
 * מחרוזות קליניות לכל כלל יתווספו עם rule_pack ב-Part 2; טקסט UI מלא ב-Part 3.
 */
import type { Dictionary } from "../keys.js";

export const he: Dictionary = {
  // רמות טריאז'
  "triage.RED": "חירום",
  "triage.YELLOW": "זהירות",
  "triage.GREEN": "יציב",
  // המלצות פעולה
  "disposition.er_now": "פנה/י מיד למיון.",
  "disposition.hold_glp1_reassess": "השהה/י את מנת ה-GLP-1 והערך/י מחדש את התרופות הפומיות.",
  "disposition.continue": "יציב — המשך/י בתוכנית הנוכחית עם מעקב.",
  // צירי סיכון
  "risk.underexposure": "תת-חשיפה (ירידה בספיגה)",
  "risk.delayed_onset": "תחילת פעולה מושהית (הסטת Tmax ימינה)",
  "risk.overexposure": "חשיפת יתר (ירידה בפינוי)",
  "risk.free_fraction_misleading": "רמה כוללת מטעה (עלייה במקטע החופשי)",
  // שמות בדיקות מעבדה
  "lab.egfr": "eGFR",
  "lab.crp": "חלבון C-תגובתי (CRP)",
  "lab.tsh": "TSH",
  "lab.ferritin": "פריטין",
  "lab.tsat": "רוויון טרנספרין",
  "lab.alt_ast": "ALT / AST",
  "lab.inr": "INR",
  "lab.albumin": "אלבומין",
};
