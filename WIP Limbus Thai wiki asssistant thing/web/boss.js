const state = { boss: null, editorDirty: false };

const $ = (id) => document.getElementById(id);


const SKILL_TAGS = {
  WinDuel: ["Clash Win", "#f95e00"],
  WhenUse: ["On Use", "#27cefe"],
  EndCoin: ["After Current Coin Attack", "#93f03f"],
  EndSkill: ["After Attack", "#93f03f"],
  AllyKill: ["On Ally Kill", "#93f03f"],
  CantDuel: ["Unclashable", "#fe0000"],
  EndBattle: ["Turn End", "#93f03f"],
  BeforeHit: ["Before Getting Hit", "#93f03f"],
  EnemyKill: ["On Kill", "#93f03f"],
  DuelGuard: ["Clashable Guard", "#93f03f"],
  BeforeUse: ["Before Use", "#93f03f"],
  DefeatDuel: ["Hit after Clash Lose", "#fe0000"],
  TargetKill: ["On Target Kill", "#93f03f"],
  DuelCounter: ["Clashable Counter", "#f95e00"],
  StartBattle: ["Combat Start", "#93f03f"],
  EndSkillTail: ["Tails Attack End", "#c90080"],
  EndSkillHead: ["Heads Attack End", "#fe59c0"],
  BeforeAttack: ["Before Attack", "#93f03f"],
  CanDuelGuard: ["Clashable Guard", "#9f6a3a"],
  AllyKillFail: ["On Ally Kill Fail", "#93f03f"],
  CantIdentify: ["Indiscriminate", "#fe0000"],
  WinDuelAttack: ["Hit after Clash Win", "#93f03f"],
  EnemyKillFail: ["Failed Kill", "#93f03f"],
  OnDefeatEvade: ["Failed Evade", "#fe0000"],
  OnSucceedEvade: ["On Evade", "#93f03f"],
  OnSucceedAttack: ["On Hit", "#93f03f"],
  TurnStartBattle: ["Turn Start", "#93f03f"],
  CantChangeTarget: ["Target Fixed", "#93f03f"],
  DefeatDuelAttack: ["Hit after Clash Lose", "#93f03f"],
  WinDuelAttackHead: ["Heads Hit after Clash Win", "#93f03f"],
  CriticalActivated: ["On Crit", "#93f03f"],
  StartBattle_Force: ["Combat Start", "#93f13e"],
  OnSucceedAttackTail: ["Tails Hit", "#93f03f"],
  OnSucceedAttackHead: ["Heads Hit", "#c6fe94"],
  CriticalOnSucceedAttack: ["On Crit", "#93f03f"],
  CriticalEnemyTargetKill: ["On Crit Kill Against Enemy", "#93f03f"],
  ReUseOnSucceedAttackHead: ["Reuse - Heads Hit", "#93f03f"],
  CriticalEnemyTargetKillFail: ["On Crit Kill Fail Against Enemy", "#93f03f"],
  UnBrokenCoinOnSucceedAttack: ["On Hit without Cracking", "#93f03f"],
};
const LABEL_TAGS = Object.fromEntries(Object.values(SKILL_TAGS).map(([label, color]) => [label, [label, color]]));

function esc(value) {
  return String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}


function slotLabel(slot) {
  const raw = String(slot || "skill");
  const match = raw.match(/^skill_(\d+)$/);
  if (match) return `Skill ${match[1]}`;
  if (raw === "defense") return "Defense";
  return raw.replace(/_/g, " ");
}

function assetUrl(bossId, group, key) {
  return `/assets/boss/${encodeURIComponent(bossId)}/${encodeURIComponent(group)}/${encodeURIComponent(String(key))}`;
}

function firstBodyPart(boss) {
  return (boss.body_parts || [])[0] || {};
}

function stat(label, value) {
  if (value === undefined || value === null || value === "") return "";
  return `<div class="stat-box"><b>${esc(label)}</b><span>${esc(value)}</span></div>`;
}


function bossStatusIndex(boss, token) {
  const clean = String(token || "").replace(/\.png$/i, "").trim().toLowerCase();
  return (boss.unique_statuses || []).findIndex((status) => {
    return [status.status_key, status.source_name].filter(Boolean).some((value) => String(value).trim().toLowerCase() === clean);
  });
}

function bossTokenImageSrc(boss, token) {
  const uniqueIndex = bossStatusIndex(boss, token);
  if (uniqueIndex >= 0 && boss.unique_statuses?.[uniqueIndex]?.icon_path) {
    return assetUrl(boss.boss_id, "status", uniqueIndex);
  }
  return `/assets/status/${encodeURIComponent(token)}`;
}

function bossTokenLabel(boss, token) {
  const uniqueIndex = bossStatusIndex(boss, token);
  if (uniqueIndex >= 0) {
    return boss.unique_statuses[uniqueIndex].source_name || boss.unique_statuses[uniqueIndex].status_key || token;
  }
  return String(token || "").replace(/\.png$/i, "");
}

function coinEffectBadge(token, boss = state.boss) {
  const match = String(token || "").match(/^CoinEffect(\d+)$/i);
  if (!match) return null;
  const label = `Coin ${match[1]}`;
  return `<img class="coin-effect" src="${assetUrl(boss.boss_id, "coin", `CoinEffect${match[1]}`)}" alt="${label}" onerror="this.replaceWith(document.createTextNode('${label}'))" />`;
}


function cleanSkillTextLine(value) {
  return String(value || "")
    .replace(/\[([^\]]{2,90})\]\s+\1\b/gi, "[$1]")
    .replace(/\[([^\]]+?)\s+([^\]]+?)\]\s+\1\s+\[\2\]/gi, "[$1 $2]")
    .replace(/\[(Unlock(?: - [IVX]+)?)\]\s+Unlock\b/gi, "[$1]")
    .replace(/\s+/g, " ")
    .trim();
}

function formatBossRich(value, boss = state.boss) {
  const safe = esc(cleanSkillTextLine(value));
  return safe.replace(/\[([^\]]+)\]/g, (full, token) => {
    const tag = SKILL_TAGS[token] || LABEL_TAGS[token];
    if (tag) return `<span class="skill-tag" style="--tag-color:${tag[1]}">[${tag[0]}]</span>`;
    const coin = coinEffectBadge(token, boss);
    if (coin) return coin;
    const label = esc(bossTokenLabel(boss, token));
    const src = bossTokenImageSrc(boss, token);
    return `<span class="status-token"><img src="${src}" alt="" onerror="this.remove()" /><span>${label}</span></span>`;
  }).replace(/\n/g, "<br />");
}

function joinWrappedLines(lines) {
  const result = [];
  for (const line of lines || []) {
    const value = cleanSkillTextLine(line);
    if (!value) continue;
    if (result.length && /^(Count|stage \(|next turn|this turn|\+\d+)/i.test(value)) {
      result[result.length - 1] += ` ${value}`;
    } else if (result.length && !/^\[|^- /.test(value) && /^(Gain|Inflict|Deal|Apply|Convert|At |Final Power|Clash Power|Coin Power)/i.test(value) === false && result[result.length - 1].endsWith("[On Use]")) {
      result[result.length - 1] += ` ${value}`;
    } else {
      result.push(value);
    }
  }
  return result;
}

function skillById(boss) {
  const map = new Map();
  (boss.skills || []).forEach((skill) => map.set(skill.skill_id, skill));
  return map;
}

async function searchBosses(query = "") {
  const res = await fetch(`/bosses/search?q=${encodeURIComponent(query)}&limit=12`);
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  const payload = await res.json();
  renderResults(payload.items || []);
  if ((payload.items || []).length && !state.boss) {
    await loadBoss(payload.items[0].boss_id);
  }
}

function renderResults(items) {
  const box = $("bossResults");
  if (!items.length) {
    box.innerHTML = `<div class="empty">No boss found.</div>`;
    return;
  }
  box.innerHTML = items.map((item) => `
    <button class="result-btn" type="button" data-boss-id="${esc(item.boss_id)}">
      <strong>${esc(item.name_en || item.boss_id)}</strong>
      <span>${esc(item.name_th || item.review_status || item.source || "")}</span>
    </button>
  `).join("");
  box.querySelectorAll("button[data-boss-id]").forEach((button) => {
    button.addEventListener("click", () => loadBoss(button.dataset.bossId));
  });
}

async function loadBoss(bossId) {
  const res = await fetch(`/bosses/${encodeURIComponent(bossId)}`);
  if (!res.ok) throw new Error(`Boss load failed: ${res.status}`);
  state.boss = await res.json();
  renderBoss(state.boss);
}

function renderBoss(boss) {
  const part = firstBodyPart(boss);
  $("bossMeta").textContent = `${boss.boss_id || "boss"} / Lv ${boss.level ?? "?"} / ${boss.review_status || boss.source || "draft"}`;
  $("bossName").textContent = boss.name_en || boss.boss_id || "Unknown boss";
  $("bossSub").textContent = boss.name_th || boss.fixture_warning || boss.source_url || "Manual fixture";
  $("bossImage").src = assetUrl(boss.boss_id, "image", "moving_sprite");
  $("bossImage").onerror = () => { $("bossImage").src = assetUrl(boss.boss_id, "image", "idle_sprite"); };

  const stagger = (part.stagger_thresholds || []).map((item) => typeof item === "object" ? `${item.percent}% (${item.hp} HP)` : `${item}%`).join(" / ");
  $("bossStats").innerHTML = [
    stat("HP", boss.hp || part.hp),
    stat("DEF", boss.defense_level || part.defense_level),
    stat("Speed", boss.speed_range || part.speed_range),
    stat("Slots", part.slot_weight),
    stat("Stagger", stagger),
    stat("Phase", (boss.phases || []).length || "-")
  ].join("");

  const warnings = [...(boss.warnings || [])].slice(0, 4);
  $("bossWarnings").innerHTML = warnings.map((item) => `<span class="warning-pill">${esc(item)}</span>`).join("");
  renderPhases(boss);
  renderStatuses(boss);
  renderPassives(boss);
  renderSkills(boss);
  renderRotation(boss);
  renderReviewEditor(boss);
}

function renderPhases(boss) {
  const phases = boss.phases || [];
  if (!phases.length) {
    $("bossPhases").innerHTML = `<div class="empty">No phase data.</div>`;
    return;
  }
  $("bossPhases").classList.remove("empty");
  $("bossPhases").innerHTML = phases.map((phase) => {
    const hpStop = phase.hp_stop ? `<p><b>HP stop:</b> ${esc(phase.hp_stop.percent)}% (${esc(phase.hp_stop.hp)} HP)</p>` : "";
    const thresholds = (phase.thresholds || []).map((item) => `<li>${esc(item.percent)}% (${esc(item.hp)} HP)</li>`).join("");
    const notes = (phase.notes || []).map((note) => `<li>${esc(note)}</li>`).join("");
    return `<article class="phase-card"><h4>Phase ${esc(phase.phase)}</h4>${hpStop}${thresholds ? `<ul>${thresholds}</ul>` : ""}${notes ? `<ul>${notes}</ul>` : ""}</article>`;
  }).join("");
}

function renderStatuses(boss) {
  const statuses = boss.unique_statuses || [];
  if (!statuses.length) {
    $("bossStatuses").innerHTML = `<div class="empty">No unique statuses captured.</div>`;
    return;
  }
  $("bossStatuses").classList.remove("empty");
  $("bossStatuses").innerHTML = statuses.map((status, index) => {
    const icon = status.icon_path ? `<img src="${assetUrl(boss.boss_id, "status", index)}" alt="" />` : `<span class="status-dot"></span>`;
    return `<article class="status-card">${icon}<span>${esc(status.source_name || status.status_key)}</span></article>`;
  }).join("");
}

function renderPassives(boss) {
  const passives = boss.passives || [];
  const counter = $("passiveCount");
  if (counter) counter.textContent = passives.length ? `${passives.length} captured` : "";
  const box = $("bossPassives");
  if (!box) return;
  if (!passives.length) {
    box.classList.add("empty");
    box.innerHTML = `<div class="empty">No passives captured.</div>`;
    return;
  }
  box.classList.remove("empty");
  box.innerHTML = passives.map((passive) => {
    const lines = joinWrappedLines(passive.description_lines || passive.effects || []);
    const body = lines.length
      ? lines.map((line) => `<div class="rule-line">${formatBossRich(line, boss)}</div>`).join("")
      : `<div class="muted">No passive text captured.</div>`;
    return `<article class="passive-card">
      <h4>${esc(passive.name_en || passive.passive_id || "Passive")}</h4>
      ${body}
    </article>`;
  }).join("");
}

function renderSkills(boss) {
  const skills = boss.skills || [];
  $("skillCount").textContent = `${skills.length} captured`;
  if (!skills.length) {
    $("bossSkills").innerHTML = `<div class="empty">No skills captured.</div>`;
    return;
  }
  $("bossSkills").classList.remove("empty");
  $("bossSkills").innerHTML = skills.map((skill) => {
    const coinPower = Number(skill.coin_power || 0);
    const chips = [skill.damage_type_hint, skill.affinity, skill.skill_type].filter(Boolean).map((item) => `<span>${esc(item)}</span>`).join("");
    const numberItems = [
      skill.base_power != null ? `Base ${skill.base_power}` : null,
      skill.coin_power != null ? `Coin ${coinPower >= 0 ? "+" : ""}${skill.coin_power}${skill.coin_count ? ` x${skill.coin_count}` : ""}` : null,
      skill.attack_weight != null ? `Atk Weight ${skill.attack_weight}` : null,
      skill.attack_level_text || null,
    ].filter(Boolean).map((item) => `<span>${formatBossRich(item, boss)}</span>`).join("");
    const icon = skill.asset_path ? `<img class="skill-icon" src="${assetUrl(boss.boss_id, "skill", skill.skill_id)}" alt="" loading="lazy" />` : `<img class="skill-icon" alt="" />`;
    const descLines = joinWrappedLines(skill.description_lines || skill.effects || []);
    const desc = descLines.length ? `<p>${descLines.map((line) => formatBossRich(line, boss)).join("<br />")}</p>` : `<p class="muted">No skill text captured yet.</p>`;
    const coinRows = (skill.coin_effect_lines || []).length
      ? (skill.coin_effect_lines || []).map((line) => `<li class="coin-row"><span>${formatBossRich(line, boss)}</span></li>`).join("")
      : `<li class="muted">Coin text needs review for this skill.</li>`;
    return `<article class="skill boss-skill">
      <div class="skill-main">
        ${icon}
        <div class="skill-copy">
          <div class="skill-name-line">
            <span class="slot">${esc(slotLabel(skill.slot || "skill"))}</span>
            <h4>${esc(skill.name_en || skill.skill_id)}</h4>
          </div>
          <div class="skill-numbers">${numberItems}</div>
        </div>
      </div>
      <div class="chips">${chips}</div>
      ${desc}
      <ul>${coinRows}</ul>
    </article>`;
  }).join("");
}

function skillName(map, id) {
  const skill = map.get(id);
  return skill ? (skill.name_en || id) : id;
}

function rotationSkillItems(row) {
  if (Array.isArray(row)) return row;
  return (row.skill_ids || row.skills || []).map((item) => typeof item === "string" ? { skill_id: item } : item);
}

function rotationSkillLabel(map, item) {
  const id = typeof item === "string" ? item : item.skill_id;
  const fallback = typeof item === "object" ? item.name_en : null;
  return fallback || skillName(map, id) || id;
}

function renderRotationRows(rows, map) {
  return rows.map((row, index) => {
    const items = rotationSkillItems(row);
    const skillRefs = items.map((item, slotIndex) => {
      const id = typeof item === "string" ? item : item.skill_id;
      const label = rotationSkillLabel(map, item);
      return `<span class="skill-ref" title="${esc(id || label)}"><b>${slotIndex + 1}</b> ${esc(label)}</span>`;
    }).join("");
    const rowNotes = Array.isArray(row) ? [] : [row.pattern, row.condition, row.note, ...(row.notes || [])].filter(Boolean);
    const notes = rowNotes.map((item) => `<div class="rule-line">${esc(item)}</div>`).join("");
    return `<div class="rotation-row"><div class="row-name">Row ${Array.isArray(row) ? index + 1 : (row.row ?? index + 1)}</div><div class="row-skills">${skillRefs || `<span class="empty">No skills captured</span>`}</div>${notes}</div>`;
  }).join("");
}

function renderRawRotation(rotation, boss) {
  const rawLines = (rotation.raw_lines || [])
    .map((line) => cleanSkillTextLine(line))
    .filter(Boolean)
    .filter((line) => !/^id=\"Behavior\">Behavior$/i.test(line));
  const dialogueIndex = rawLines.findIndex((line) => /^Dialogue$/i.test(line));
  const behaviorLines = dialogueIndex >= 0 ? rawLines.slice(0, dialogueIndex) : rawLines;
  if (!behaviorLines.length) return `<div class="empty">No rotation captured yet.</div>`;

  return `<article class="rotation-card raw-rotation">
    <h4>Behavior / Attack Pattern</h4>
    ${behaviorLines.map((line) => {
      if (/^(Attack Pattern|Behavior)$/i.test(line)) return `<h5>${esc(line)}</h5>`;
      if (line.startsWith("- ")) return `<div class="rotation-bullet">${formatBossRich(line, boss)}</div>`;
      return `<div class="rule-line">${formatBossRich(line, boss)}</div>`;
    }).join("")}
  </article>`;
}

function renderRotation(boss) {
  const rotation = boss.skill_rotation || {};
  const map = skillById(boss);
  const phases = [rotation.phase_1, rotation.phase_2].filter(Boolean);
  $("rotationSource").textContent = rotation.source || "draft";
  if (!phases.length) {
    $("bossRotation").classList.remove("empty");
    $("bossRotation").innerHTML = renderRawRotation(rotation, boss);
    return;
  }
  $("bossRotation").classList.remove("empty");
  const phaseHtml = phases.map((phase) => {
    const rows = renderRotationRows(phase.rotation_rows || [], map);
    const conditionals = (phase.conditional_patterns || []).map((item) => {
      const conditionalRows = item.rotation_rows ? renderRotationRows(item.rotation_rows, map) : "";
      return `<div class="conditional-pattern"><div class="rule-line"><b>${esc(item.condition || item.note || "Conditional pattern")}</b></div>${conditionalRows}</div>`;
    }).join("");
    const phaseNotes = [phase.phase_end, ...(phase.notes || [])].filter(Boolean).map((item) => `<div class="rule-line">${esc(item)}</div>`).join("");
    return `<article class="rotation-card phase-${esc(phase.phase)}"><h4>Phase ${esc(phase.phase)}</h4>${phaseNotes}${rows}${conditionals}</article>`;
  }).join("");
  const phaseInterrupts = phases.flatMap((phase) => (phase.interrupts || []).map((item) => ({ ...item, phase: phase.phase })));
  const allInterrupts = [...(rotation.interrupts || []), ...phaseInterrupts];
  const interrupts = allInterrupts.map((item) => {
    const skill = item.skill_id || item.insert_skill?.skill_id || item.replace_skill?.to;
    const label = item.insert_skill?.name_en || (skill ? skillName(map, skill) : "");
    return `<li>${item.phase ? `Phase ${esc(item.phase)}: ` : ""}${esc(item.trigger || item.condition || item.note || "Interrupt")}${label ? `: ${esc(label)}` : ""}${item.notes ? ` ? ${esc(item.notes)}` : ""}</li>`;
  }).join("");
  const questions = (rotation.open_questions || []).map((item) => `<li>${esc(item)}</li>`).join("");
  $("bossRotation").innerHTML = phaseHtml + (interrupts ? `<article class="note-card"><h3>Interrupts</h3><ul>${interrupts}</ul></article>` : "") + (questions ? `<article class="note-card"><h3>Needs Review</h3><ul>${questions}</ul></article>` : "");
}


function cloneJson(value) {
  return JSON.parse(JSON.stringify(value ?? null));
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function parseEditorJson(id) {
  try {
    return JSON.parse($(id).value || "null");
  } catch (error) {
    throw new Error(`${id}: ${error.message}`);
  }
}

function bossCoreForEditor(boss) {
  const skip = new Set(["skills", "passives", "unique_statuses", "skill_rotation", "review"]);
  const core = {};
  Object.entries(boss || {}).forEach(([key, value]) => {
    if (!skip.has(key)) core[key] = value;
  });
  return core;
}

function setSelectValue(id, value) {
  const select = $(id);
  if (!select) return;
  select.value = value || "draft";
}

function renderReviewEditor(boss) {
  if (!boss) return;
  const review = boss.review || {};
  const sections = review.sections || {};
  $("reviewCore").value = pretty(bossCoreForEditor(boss));
  $("reviewSkills").value = pretty(boss.skills || []);
  $("reviewStatuses").value = pretty(boss.unique_statuses || []);
  $("reviewRotation").value = pretty(boss.skill_rotation || {});
  setSelectValue("reviewCoreStatus", sections.core || sections.stats || "draft");
  setSelectValue("reviewSkillsStatus", sections.skills || "draft");
  setSelectValue("reviewStatusesStatus", sections.statuses || "draft");
  setSelectValue("reviewRotationStatus", sections.rotation || "draft");
  if (review.reviewed_by) $("reviewerName").value = review.reviewed_by;
  $("reviewSaveStatus").textContent = boss.reviewed_override ? "Loaded reviewed override" : "Draft loaded";
  state.editorDirty = false;
}

function buildReviewedBossFromEditor() {
  if (!state.boss) throw new Error("No boss selected");
  const core = parseEditorJson("reviewCore");
  const skills = parseEditorJson("reviewSkills");
  const statuses = parseEditorJson("reviewStatuses");
  const rotation = parseEditorJson("reviewRotation");
  if (!core || typeof core !== "object" || Array.isArray(core)) throw new Error("Core must be a JSON object");
  if (!Array.isArray(skills)) throw new Error("Skills must be a JSON array");
  if (!Array.isArray(statuses)) throw new Error("Statuses must be a JSON array");
  if (!rotation || typeof rotation !== "object" || Array.isArray(rotation)) throw new Error("Skill rotation must be a JSON object");
  return {
    ...cloneJson(state.boss),
    ...core,
    skills,
    unique_statuses: statuses,
    skill_rotation: rotation,
    review: {
      ...(state.boss.review || {}),
      reviewed_by: $("reviewerName").value.trim() || "local_admin",
      sections: {
        core: $("reviewCoreStatus").value,
        skills: $("reviewSkillsStatus").value,
        statuses: $("reviewStatusesStatus").value,
        rotation: $("reviewRotationStatus").value
      }
    }
  };
}

function reviewPayload() {
  const boss = buildReviewedBossFromEditor();
  return {
    boss_id: boss.boss_id,
    reviewed_by: $("reviewerName").value.trim() || "local_admin",
    review_status: "reviewed_local",
    sections: boss.review.sections,
    boss
  };
}

function markEditorDirty() {
  state.editorDirty = true;
  $("reviewSaveStatus").textContent = "Unsaved edits";
}

function applyReviewPreview() {
  try {
    const boss = buildReviewedBossFromEditor();
    state.boss = boss;
    renderBoss(boss);
    $("reviewSaveStatus").textContent = "Preview applied, not saved";
  } catch (error) {
    $("reviewSaveStatus").textContent = error.message;
  }
}

async function saveReview() {
  try {
    const payload = reviewPayload();
    const res = await fetch("/bosses/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const body = await res.json();
    if (!res.ok || !body.ok) throw new Error(body.message || body.error || `Save failed: ${res.status}`);
    state.boss = body.boss;
    renderBoss(state.boss);
    $("reviewSaveStatus").textContent = `Saved ${body.path}`;
  } catch (error) {
    $("reviewSaveStatus").textContent = error.message;
  }
}

function downloadReview() {
  try {
    const boss = buildReviewedBossFromEditor();
    const blob = new Blob([pretty(boss) + "\n"], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${boss.boss_id || "boss"}.reviewed.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    $("reviewSaveStatus").textContent = "Download prepared";
  } catch (error) {
    $("reviewSaveStatus").textContent = error.message;
  }
}

$("bossSearch").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.boss = null;
  const query = $("bossQuery").value.trim();
  const params = new URLSearchParams(window.location.search);
  if (query) {
    params.set("q", query);
  } else {
    params.delete("q");
  }
  params.delete("boss");
  const nextUrl = `${window.location.pathname}${params.toString() ? `?${params}` : ""}`;
  window.history.replaceState(null, "", nextUrl);
  await searchBosses(query);
});


["reviewCore", "reviewSkills", "reviewStatuses", "reviewRotation", "reviewerName", "reviewCoreStatus", "reviewSkillsStatus", "reviewStatusesStatus", "reviewRotationStatus"].forEach((id) => {
  const el = $(id);
  if (el) el.addEventListener("input", markEditorDirty);
  if (el) el.addEventListener("change", markEditorDirty);
});
$("applyReview").addEventListener("click", applyReviewPreview);
$("saveReview").addEventListener("click", saveReview);
$("downloadReview").addEventListener("click", downloadReview);

async function bootBossPage() {
  const params = new URLSearchParams(window.location.search);
  const query = params.get("q") || "";
  const bossId = params.get("boss") || "";
  $("bossQuery").value = query;
  if (bossId) {
    await searchBosses(query);
    await loadBoss(bossId);
    return;
  }
  await searchBosses(query);
}

bootBossPage().catch((error) => {
  $("bossResults").innerHTML = `<div class="empty">${esc(error.message)}</div>`;
});
