/**
 * מילון עברית (locale "he", RTL). מחרוזות קליניות מלאות ל-v5.
 * מפתחות admin.* מופיעים רק בשכבת הרופא/אדמין, לעולם לא בתצוגת המטופל.
 */
import type { Dictionary } from "../keys.js";

export const he: Dictionary = {
  "triage.red.emergency": "אדום — נדרשת הערכה מיידית במלר\"ד",
  "triage.yellow.hold_and_reassess": "צהוב — להשהות העלאת מינון GLP-1 ולבחון מחדש את הטיפול הפומי",
  "triage.green.stable": "ירוק — מצב יציב, להמשיך מעקב",

  "action.lt4_check_tsh_4w": "לבדוק TSH לאחר 4 שבועות תחת PPI",
  "action.lt4_consider_liquid_formulation": "לשקול מעבר ללבותירוקסין נוזלי או softgel (פחות תלוי pH)",
  "action.lt4_review_cation_spacing": "לוודא הפרדה של 4 שעות לפחות בין לבותירוקסין לסידן/ברזל/מגנזיום/אלומיניום",
  "action.lt4_enforce_4h_separation": "להקפיד על הפרדה של 4 שעות לפחות בין לבותירוקסין לקטיונים רב-ערכיים",
  "patient.lt4_separate_from_ppi": "ליטול לבותירוקסין על קיבה ריקה 30–60 דקות לפני ה-PPI ולפני ארוחת הבוקר",
  "patient.lt4_fasting_30min_morning": "לבותירוקסין — בבוקר על קיבה ריקה; לא לאכול ולא לשתות דבר חוץ ממים במשך 30–60 דקות",
  "patient.lt4_separate_from_minerals_4h": "תכשירי סידן, ברזל, מגנזיום ואלומיניום — לפחות 4 שעות אחרי הלבותירוקסין",
  "lab.tsh_4w": "TSH לאחר 4 שבועות",
  "lab.ft4_4w": "T4 חופשי לאחר 4 שבועות",
  "admin.lt4_tablet_ph_dissolution_failure": "[admin] כישלון המסה של טבליית LT4 בסביבת pH מוגבר",
  "admin.lt4_cation_chelation": "[admin] קישור LT4 לקטיונים רב-ערכיים בלומן",

  "action.iron_check_ferritin_tsat_crp": "מעקב פריטין, רוויית טרנספרין ו-CRP לאחר 8 שבועות",
  "action.iron_consider_iv_if_poor_response": "אם התגובה אינה מספקת תוך 8 שבועות — לשקול ברזל IV",
  "action.iron_consider_bisglycinate": "לשקול מעבר לברזל ביסגליצינאט — סבילות טובה יותר ופחות תלוי בחומציות",
  "patient.iron_with_vitamin_c": "ליטול ברזל יחד עם ויטמין C (100 מ\"ג) לשיפור הספיגה",
  "patient.iron_separate_from_calcium_dairy": "לא ליטול ברזל יחד עם מוצרי חלב, קפה, תה או תכשירי סידן",
  "lab.hb_8w": "המוגלובין לאחר 8 שבועות",
  "lab.ferritin_8w": "פריטין לאחר 8 שבועות",
  "lab.tsat_8w": "רוויית טרנספרין לאחר 8 שבועות",
  "lab.crp_8w": "CRP לאחר 8 שבועות",
  "admin.iron_ph_failure": "[admin] כישלון סולוביליזציה של Fe³⁺→Fe²⁺ ב-pH מוגבר",

  "action.oc_recommend_nonoral_or_barrier_4w": "להמליץ על אמצעי מניעה לא פומי או חוצץ במשך 4 השבועות הראשונים לאחר התחלת טירזפטיד וכל העלאת מינון (לפי FDA)",
  "patient.oc_use_backup_4w_after_start_and_each_escalation": "להשתמש באמצעי מניעה גיבוי (קונדום או התקן תוך-רחמי) במשך 4 השבועות הראשונים לאחר התחלת טירזפטיד ולאחר כל העלאת מינון",
  "admin.glp1_oc_absorption_drop": "[admin] האטת ריקון קיבה → ירידה בספיגת הורמונים פומיים",

  "action.furosemide_consider_iv_or_switch": "לשקול פורוסמיד IV או מעבר לטורסמיד / בומטניד (זמינות ביולוגית צפויה יותר)",
  "action.furosemide_assess_congestion_objectively": "הערכה אובייקטיבית של גודש: משקל, תפוקת שתן, צילום חזה, NT-proBNP, אולטרסאונד ריאות",
  "patient.daily_weight_log": "שקילה יומית באותה שעה; לדווח על עלייה מעל 1 ק\"ג ביממה או 2 ק\"ג ב-3 ימים",
  "lab.creat_1w": "קריאטינין לאחר שבוע",
  "lab.na_1w": "נתרן לאחר שבוע",
  "lab.k_1w": "אשלגן לאחר שבוע",
  "admin.furosemide_gut_edema": "[admin] איבוד זמינות ביולוגית של פורוסמיד פומי עם בצקת קיר המעי",

  "action.doac_check_label_renal_dose": "לבדוק עלון: התאמת מינון DOAC בירידת GFR הינה חובה",
  "action.doac_consider_vka_if_egfr_below_30": "ב-eGFR <30 מ\"ל/דקה — לשקול מעבר לוורפרין עם מעקב INR",
  "patient.bleeding_signs_education": "לדווח מיידית על דימום: חניכיים, אף, דם בשתן/צואה, חבורות ללא סיבה",
  "lab.egfr_4w": "eGFR לאחר 4 שבועות",
  "admin.doac_renal_accumulation": "[admin] הצטברות כלייתית של DOAC עם סיכון לדימום",

  "action.cirrhosis_consider_dose_reduction": "צירוזיס Child-Pugh B/C — לשקול הפחתת מינון של תרופות עם first-pass גבוה",
  "action.cirrhosis_check_label_hepatic_section": "לעיין בעלון בסעיף אי-ספיקה כבדית",
  "patient.report_sedation_confusion_immediately": "לדווח מיידית על נמנום, בלבול או תגובה מואטת",
  "lab.alt_4w": "ALT לאחר 4 שבועות",
  "lab.ast_4w": "AST לאחר 4 שבועות",
  "lab.inr_4w": "INR לאחר 4 שבועות",
  "lab.albumin_4w": "אלבומין לאחר 4 שבועות",
  "admin.cirrhosis_first_pass": "[admin] קריסת first-pass בצירוזיס → עלייה בזמינות ביולוגית",

  "action.inflammation_watch_for_toxicity": "לעקוב אחר סימני רעילות של תרופות תלויות CYP בזמן דלקת פעילה",
  "action.inflammation_reassess_after_resolution": "לאחר חלוף הדלקת — להעריך מחדש מינון של מצעי CYP (סיכון לתת-מינון)",
  "patient.report_unusual_drowsiness_or_side_effects": "לדווח על נמנום חריג או תופעות לוואי חדשות",
  "lab.crp_2w": "CRP לאחר שבועיים",
  "admin.inflammation_cyp_suppression": "[admin] דיכוי CYP על-ידי ציטוקינים → הצטברות מצע",

  "action.fq_enforce_2_to_6h_separation": "הפרדה של פלואורוקווינולון ותכשירים מכילי קטיונים — לפחות 2–6 שעות",
  "patient.fq_separate_from_minerals_4h": "לא ליטול את הפלואורוקווינולון עם סידן, ברזל, מגנזיום או אלומיניום — להפריד לפחות 4 שעות",
  "admin.fq_cation_chelation": "[admin] קישור פלואורוקווינולון לקטיונים רב-ערכיים",

  "action.tetra_enforce_separation": "הפרדה של טטרציקלין ותכשירים מכילי קטיונים / מוצרי חלב",
  "patient.tetra_separate_from_minerals_dairy": "דוקסיציקלין — בנפרד ממוצרי חלב, סידן, ברזל, מגנזיום ואלומיניום",
  "admin.tetra_cation_chelation": "[admin] קישור טטרציקלין לקטיונים רב-ערכיים",

  "action.azole_consider_solution_or_iv": "לשקול מעבר לתמיסה פומית של איטראקונזול או למתן IV",
  "action.azole_check_trough_level": "מעקב רמת שפל (trough) של האזול (TDM)",
  "patient.azole_take_with_acidic_drink": "בקפסולות איטראקונזול — ליטול עם משקה חומצי (למשל קולה)",
  "lab.itra_trough_2w": "רמת שפל של איטראקונזול לאחר שבועיים",
  "admin.azole_ph_failure": "[admin] כישלון המסה של קפסולת אזול ב-pH מוגבר",

  "action.tmax_warn_delayed_onset": "להזהיר מפני עיכוב אפשרי בהתחלת השפעה של תרופות תלויות Tmax תחת GLP-1",
  "patient.tmax_drug_may_act_later": "התרופה עשויה להשפיע מאוחר מהרגיל בשל האטת ריקון הקיבה",
  "admin.glp1_tmax_shift": "[admin] הזזת Tmax בעקבות האטת ריקון קיבה",

  "action.digoxin_check_level": "לבדוק רמת דיגוקסין בדם",
  "action.digoxin_consider_dose_reduction": "בירידת GFR — לשקול הפחתת מינון דיגוקסין",
  "patient.digoxin_toxicity_signs_education": "סימני רעילות דיגוקסין: בחילה, הפרעות ראייה (הילות צהובות), הפרעות קצב — לדווח מיידית",
  "lab.dig_level_2w": "רמת דיגוקסין לאחר שבועיים",
  "lab.egfr_2w": "eGFR לאחר שבועיים",
  "lab.k_2w": "אשלגן לאחר שבועיים",
  "admin.digoxin_renal_accumulation": "[admin] הצטברות כלייתית של דיגוקסין (NTI)",

  "action.bariatric_doac_specialist_review": "התייעצות עם מומחה לנוגדי קרישה אם פחות מ-6 חודשים לאחר בריאטרי",
  "action.bariatric_doac_consider_lmwh_vka": "לשקול LMWH או וורפרין עם מעקב INR עד התייצבות לאחר ניתוח בריאטרי",
  "patient.thrombosis_signs_education": "סימני קרישיות: נפיחות וכאב ברגל אחת, קוצר נשימה, כאב בחזה — לפנות מיידית",
  "lab.anti_xa_2w": "פעילות אנטי-Xa לאחר שבועיים (בהינתן זמינות)",
  "admin.bariatric_doac_unpredictable": "[admin] אנטומיה משונה → חשיפת DOAC בלתי צפויה",

  "action.protein_binding_consider_free_level": "בהיפואלבומינמיה — לשקול מדידת פרקציה חופשית; הרמה הכוללת עלולה להטעות",
  "action.protein_binding_clinical_response_priority": "עדיפות לתגובה קלינית על-פני רמה כוללת",
  "admin.hypoalbuminemia_free_fraction": "[admin] פרקציה חופשית מוגברת באלבומין נמוך",

  "forecast.glp1.hold_no_escalation": "GLP-1: להשהות העלאת מינון עד חלוף תסמיני GI",
  "forecast.glp1.review_recent_escalation": "GLP-1: לבחון — העלאה אחרונה, השפעה על ריקון קיבה מקסימלית",
  "forecast.glp1.continue_standard_titration": "GLP-1: להמשיך טיטרציה סטנדרטית",
  "forecast.glp1.rationale.gi_intolerance": "אי-סבילות GI (בחילות / הקאות / חוסר יכולת לשמר תרופות או נוזלים)",
  "forecast.glp1.rationale.first_4_weeks_attenuates": "האטת ריקון הקיבה מקסימלית ב-4 השבועות הראשונים לאחר התחלה וכל העלאה, ולאחר מכן נחלשת",
  "forecast.glp1.rationale.stable_tolerance": "סבילות יציבה, ללא סמני אזהרה",

  "forecast.risk.aki_dehydration": "סיכון לפגיעה כלייתית חריפה מהתייבשות בעקבות איבודים מתמשכים — להעריך מאזן נוזלים ותרופות נפרוטוקסיות",
  "forecast.risk.doac_accumulation_low_egfr": "סיכון להצטברות DOAC עם ירידה ב-eGFR — מעקב לאחר 8 שבועות",
  "forecast.risk.orthostatic_weight_loss": "סיכון ליתר לחץ דם תנוחתי בעקבות ירידה במשקל תחת טיפול אנטי-היפרטנסיבי — בחינת מינון לאחר 8 שבועות",
  "forecast.risk.lt4_drift_ppi": "סיכון לדריפט של TSH תחת PPI — בדיקה חוזרת לאחר 6 שבועות",
  "forecast.risk.cyp_substrate_toxicity_in_inflammation": "סיכון לרעילות מצעי CYP בדלקת מתמשכת",
  "forecast.risk.stable_profile": "פרופיל יציב — מעקב שגרתי לאחר 4 שבועות",

  "adjust.doac_reduce_at_egfr_30": "הפחתת מינון DOAC ב-eGFR מתחת ל-30 (לפי עלון התרופה הספציפי)",
  "adjust.antihypertensive_taper_25_50": "הפחתה הדרגתית של מינון אנטי-היפרטנסיבי ב-25–50% עם ירידה במשקל",
  "adjust.lt4_review_dose_weight_loss": "בחינה מחדש של מינון לבותירוקסין — ירידה במשקל עשויה לדרוש התאמה",
  "adjust.antidiabetic_review_for_hypoglycemia": "בחינה מחדש של טיפול אנטי-סוכרתי — סיכון להיפוגליקמיה בתוספת GLP-1",

  "trigger.egfr_falling": "ירידה ב-eGFR",
  "trigger.expected_weight_loss": "ירידה צפויה במשקל תחת GLP-1",
  "trigger.glp1_glycemic_effect": "השפעה היפוגליקמית של GLP-1 בנוסף לטיפול הקיים",
};
