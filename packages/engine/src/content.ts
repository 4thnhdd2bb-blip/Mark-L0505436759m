/**
 * Bundled clinical content loader (Node-only).
 *
 * The canonical artifacts live as JSON under packages/engine/content/ so the
 * clinical team edits data, not code. They are version-pinned with the deploy
 * (good for SaMD). We load + validate them once with the zod schemas; a bad pack
 * fails loudly at startup rather than mid-assessment.
 *
 * createRequire is used so JSON loads identically under Node ESM and CJS without
 * import-assertion syntax. The Expo client never imports this module — it receives
 * assessments from the server.
 */
import { createRequire } from "node:module";
import { RulePack, DrugMaster } from "@metacod/shared";
import type { RulePack as RulePackT, DrugMaster as DrugMasterT } from "@metacod/shared";

const require = createRequire(import.meta.url);

let rulePackCache: RulePackT | null = null;
let drugMasterCache: DrugMasterT | null = null;

export function loadRulePack(): RulePackT {
  if (!rulePackCache) {
    rulePackCache = RulePack.parse(require("../content/rule_pack_v2.json"));
  }
  return rulePackCache;
}

export function loadDrugMaster(): DrugMasterT {
  if (!drugMasterCache) {
    drugMasterCache = DrugMaster.parse(require("../content/drug_master_v2.json"));
  }
  return drugMasterCache;
}

export function loadContent(): { rulePack: RulePackT; drugMaster: DrugMasterT } {
  return { rulePack: loadRulePack(), drugMaster: loadDrugMaster() };
}
