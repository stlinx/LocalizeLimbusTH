const state = {
  boss: null,
  bossSlots: [],
  sinners: [],
  nextSinnerId: 1,
  draggingSkill: null,
  armedSkill: null,
};

const LANG = "th";
const UPTIE = 4;
const $ = (id) => document.getElementById(id);

const SKILL_TAGS = {
  WinDuel: ["Clash Win", "#f95e00"],
  WhenUse: ["On Use", "#27cefe"],
  EndCoin: ["After Current Coin Attack", "#93f03f"],
  EndSkill: ["After Attack", "#93f03f"],
  BeforeUse: ["Before Use", "#93f03f"],
  BeforeAttack: ["Before Attack", "#93f03f"],
  StartBattle: ["Combat Start", "#93f03f"],
  CantDuel: ["Unclashable", "#fe0000"],
  OnSucceedAttack: ["On Hit", "#93f03f"],
  OnSucceedAttackHead: ["Heads Hit", "#c6fe94"],
  OnSucceedAttackTail: ["Tails Hit", "#93f03f"],
  CriticalActivated: ["On Crit", "#93f03f"],
  CriticalOnSucceedAttack: ["On Crit", "#93f03f"],
  DefeatDuel: ["Hit after Clash Lose", "#fe0000"],
  DefeatDuelAttack: ["Hit after Clash Lose", "#93f03f"],
  WinDuelAttack: ["Hit after Clash Win", "#93f03f"],
  TurnStartBattle: ["Turn Start", "#93f03f"],
  EndBattle: ["Turn End", "#93f03f"],
};
const LABEL_TAGS = Object.fromEntries(Object.values(SKILL_TAGS).map(([label, color]) => [label, [label, color]]));

function text(value, fallback = "-") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function escapeHtml(value) {
  return text(value, "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[ch]);
}

async function getJson(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || payload.error || response.statusText);
  return payload;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || payload.error || response.statusText);
  return payload;
}

function normalized(value) {
  return text(value, "").toLowerCase().replace(/\[[^\]]*\]/g, " ").replace(/[^a-z0-9]+/g, " ").trim();
}

function compact(value) {
  return normalized(value).replace(/\s+/g, "");
}

function parseRange(value, fallbackMin = 1, fallbackMax = 8) {
  const nums = text(value, "").match(/\d+/g)?.map(Number) || [];
  if (nums.length >= 2) return [Math.min(nums[0], nums[1]), Math.max(nums[0], nums[1])];
  if (nums.length === 1) return [nums[0], nums[0]];
  return [fallbackMin, fallbackMax];
}

function randomInt(min, max) {
  return min + Math.floor(Math.random() * (max - min + 1));
}

function coinPowerLine(skill) {
  const base = Number(skill?.base_power || 0);
  const coin = Number(skill?.coin_power || 0);
  const count = Number(skill?.coin_count || 0);
  return `${base} ${coin >= 0 ? "+" : ""}${coin} x${count}`;
}

function skillKey(skill) {
  return String(skill?.source_skill_text_id || skill?.skill_id || skill?.slot || "");
}

function slotLabel(slot) {
  const raw = text(slot);
  const match = raw.match(/^skill_(\d+)$/);
  if (match) return `Skill ${match[1]}`;
  if (raw === "defense") return "Defense";
  return raw.replace(/_/g, " ");
}

function identitySkillName(skill) {
  return skill?.localized_name || skill?.name?.en || skill?.name_en || "Skill";
}

function bossSkillName(skill) {
  return skill?.name_th || skill?.name_en || skill?.skill_id || "Boss Skill";
}

function bossTokenIcon(token) {
  const boss = state.boss;
  const statuses = boss?.unique_statuses || [];
  const needle = normalized(token);
  const index = statuses.findIndex((status) => [status.status_key, status.name_en, status.name_th, status.source_name].some((value) => normalized(value) === needle));
  return index >= 0 ? `/assets/boss/${encodeURIComponent(boss.boss_id)}/status/${index}` : `/assets/status/${encodeURIComponent(token)}`;
}

function formatBossRich(value) {
  return escapeHtml(value).replace(/\[([^\]]+)\]\s*([^\[\]\n<]{2,80})?/g, (full, token, following = "") => {
    const tag = SKILL_TAGS[token] || LABEL_TAGS[token];
    if (tag) return `<span class="skill-tag" style="--tag-color:${tag[1]}">[${tag[0]}]</span>${escapeHtml(following || "")}`;
    const followNorm = normalized(following);
    const tokenNorm = normalized(token);
    const shouldDropFollowing = followNorm && (followNorm === tokenNorm || compact(following) === compact(token));
    const label = shouldDropFollowing ? token : `${token}${following || ""}`.trim();
    return `<span class="status-token"><img src="${bossTokenIcon(token)}" alt="" onerror="this.remove()" /><span>${escapeHtml(label)}</span></span>`;
  }).replace(/\n/g, "<br />");
}

function formatIdentityRich(value, profile) {
  return escapeHtml(value).replace(/\[([^\]]+)\]/g, (full, token) => {
    const tag = SKILL_TAGS[token] || LABEL_TAGS[token];
    if (tag) return `<span class="skill-tag" style="--tag-color:${tag[1]}">[${tag[0]}]</span>`;
    const asset = profile?.token_assets?.[token] || {};
    const label = asset.label?.th || asset.label?.en || token;
    const src = asset.path
      ? `/assets/token/${encodeURIComponent(profile.identity.id)}/${encodeURIComponent(token)}?lang=${LANG}&uptie=${UPTIE}`
      : `/assets/status/${encodeURIComponent(token)}`;
    return `<span class="status-token"><img src="${src}" alt="" onerror="this.remove()" /><span>${escapeHtml(label)}</span></span>`;
  }).replace(/\n/g, "<br />");
}

function bossEffectText(skill) {
  const effects = [];
  if (skill.description_en) effects.push(skill.description_en);
  for (const row of skill.effects || []) effects.push(row);
  for (const coin of skill.coins || []) {
    for (const row of coin.effects || []) effects.push(`Coin ${coin.coin_index} ${row}`);
  }
  return effects.filter(Boolean).join("\n");
}

function skillById(skillId) {
  return (state.boss?.skills || []).find((skill) => skill.skill_id === skillId) || null;
}

function parseRotationRows(boss) {
  const lines = boss?.skill_rotation?.raw_lines || [];
  return lines
    .filter((line) => /^-\s+/.test(line))
    .map((line) => line.replace(/^-\s+/, "").split(/,\s*/).map((item) => item.trim()).filter(Boolean))
    .filter((row) => row.length);
}

function findBossSkill(name) {
  const direct = skillById(name);
  if (direct) return direct;
  const skills = state.boss?.skills || [];
  const needle = normalized(name);
  const needleCompact = compact(name);
  return skills.find((skill) => normalized(skill.name_en) === needle)
    || skills.find((skill) => needle.startsWith(normalized(skill.name_en)) || normalized(skill.name_en).startsWith(needle))
    || skills.find((skill) => needleCompact.includes(compact(skill.name_en)) || compact(skill.name_en).includes(needleCompact))
    || skills[0];
}

function conditionMatches(condition, turn, hpPercent) {
  if (!condition || Object.keys(condition).length === 0) return true;
  if (condition.all) return condition.all.every((item) => conditionMatches(item, turn, hpPercent));
  if (condition.any) return condition.any.some((item) => conditionMatches(item, turn, hpPercent));
  if (condition.turn_eq !== undefined && turn !== Number(condition.turn_eq)) return false;
  if (condition.turn_lte !== undefined && turn > Number(condition.turn_lte)) return false;
  if (condition.turn_gte !== undefined && turn < Number(condition.turn_gte)) return false;
  if (condition.hp_lte !== undefined && hpPercent > Number(condition.hp_lte)) return false;
  if (condition.hp_lt !== undefined && hpPercent >= Number(condition.hp_lt)) return false;
  if (condition.hp_gte !== undefined && hpPercent < Number(condition.hp_gte)) return false;
  if (condition.hp_gt !== undefined && hpPercent <= Number(condition.hp_gt)) return false;
  return true;
}

function pickBehaviorPattern(boss, turn, hpPercent) {
  const patterns = [...(boss?.boss_behavior?.patterns || [])].sort((a, b) => Number(b.priority || 0) - Number(a.priority || 0));
  return patterns.find((pattern) => conditionMatches(pattern.active_when, turn, hpPercent)) || null;
}

function pickBehaviorRow(pattern, turn) {
  const rows = pattern?.rows || [];
  if (!rows.length) return null;
  if (pattern.row_mode === "cycle") {
    const startTurn = Number(pattern.cycle_start_turn || 1);
    const index = ((turn - startTurn) % rows.length + rows.length) % rows.length;
    return rows[index];
  }
  return rows[0];
}

function behaviorIntentForTurn(boss, turn, hpPercent) {
  const pattern = pickBehaviorPattern(boss, turn, hpPercent);
  const row = pickBehaviorRow(pattern, turn);
  if (pattern && row) {
    return {
      source: boss.boss_behavior?.source || "boss_behavior",
      pattern,
      row,
      skillIds: row.skills || [],
      bossSp: Number(row.boss_sp ?? pattern.boss_sp ?? 0),
      speedBonus: Number(row.speed_bonus ?? pattern.speed_bonus ?? 0),
      notes: [
        ...(boss.boss_behavior?.notes || []),
        ...(pattern.notes || []),
        ...(row.notes || []),
      ],
    };
  }
  const rows = parseRotationRows(boss);
  if (!rows.length) return {
    source: "fallback skill list",
    pattern: null,
    row: null,
    skillIds: (boss.skills || []).slice(0, 3).map((skill) => skill.skill_id || skill.name_en),
    bossSp: 0,
    speedBonus: 0,
    notes: ["No structured boss_behavior or raw rotation rows were found."],
  };
  if (turn <= 2 && hpPercent > 90) return { source: "raw skill_rotation fallback", pattern: null, row: null, skillIds: rows[0], bossSp: 0, speedBonus: 0, notes: ["Fallback from raw wiki behavior text."] };
  if ((hpPercent <= 90 || turn >= 3) && hpPercent > 80) return { source: "raw skill_rotation fallback", pattern: null, row: null, skillIds: rows[1] || rows[0], bossSp: 10, speedBonus: 0, notes: ["Fallback from raw wiki behavior text."] };
  const cycle = [rows[2], rows[3], rows[4]].filter(Boolean);
  const rowFallback = cycle[(turn - 5 + cycle.length * 10) % cycle.length] || rows[1] || rows[0];
  return { source: "raw skill_rotation fallback", pattern: null, row: null, skillIds: rowFallback, bossSp: hpPercent <= 40 ? 30 : 20, speedBonus: 0, notes: ["Fallback from raw wiki behavior text."] };
}

function renderBehaviorNotes(intent) {
  const root = $("behaviorNotes");
  if (!root) return;
  const pattern = intent?.pattern;
  const row = intent?.row;
  if (!intent) {
    root.classList.add("empty");
    root.textContent = "Generate boss intent to view behavior rules.";
    return;
  }
  root.classList.remove("empty");
  const effects = [
    ...(pattern?.start_effects || []),
    ...(row?.start_effects || []),
    ...(pattern?.turn_end_effects || []),
    ...(row?.turn_end_effects || []),
  ];
  const summons = (pattern?.summon_rules || []).flatMap((rule) => rule.summons || []);
  root.innerHTML = `
    <article>
      <strong>${escapeHtml(pattern?.label || intent.source)}</strong>
      <span>${escapeHtml(row?.row_id || "row")}</span>
      <p>${escapeHtml((intent.notes || [])[0] || "Structured behavior selected for this turn.")}</p>
      <div class="behavior-pills">
        <span>SP ${escapeHtml(intent.bossSp)}</span>
        <span>Speed ${intent.speedBonus >= 0 ? "+" : ""}${escapeHtml(intent.speedBonus)}</span>
        <span>${escapeHtml(intent.skillIds.length)} slots</span>
        ${pattern?.review_status ? `<span>${escapeHtml(pattern.review_status)}</span>` : ""}
      </div>
      ${effects.length ? `<ul>${effects.map((effect) => `<li>${escapeHtml(effect.type || "effect")}${effect.status ? `: ${escapeHtml(effect.status)}` : ""}${effect.amount !== undefined ? ` ${escapeHtml(effect.amount)}` : ""}</li>`).join("")}</ul>` : ""}
      ${summons.length ? `<ul>${summons.map((summon) => `<li>Summon ${escapeHtml(summon.count || 1)} ${escapeHtml(summon.enemy_name || "enemy")}</li>`).join("")}</ul>` : ""}
    </article>
  `;
}

async function generateBossIntent() {
  if (!state.boss) return;
  const turn = Math.max(1, Number($("turnNumber").value || 1));
  const hpPercent = Math.max(1, Math.min(100, Number($("bossHpPercent").value || 100)));
  let intent;
  try {
    intent = await getJson(`/bosses/${encodeURIComponent(state.boss.boss_id)}/intent?turn=${encodeURIComponent(turn)}&hp_percent=${encodeURIComponent(hpPercent)}`);
  } catch (error) {
    intent = behaviorIntentForTurn(state.boss, turn, hpPercent);
  }
  const [speedMin, speedMax] = parseRange(intent.speed_range || state.boss.speed_range || state.boss.body_parts?.[0]?.speed_range, 1, 8);
  const slotRefs = intent.slots?.length ? intent.slots.map((slot) => slot.skill_id || slot.skill_ref) : (intent.skillIds || []);
  state.bossSlots = slotRefs.map((skillId, index) => ({
    id: `boss-${turn}-${index}`,
    index: index + 1,
    speed: Math.max(1, randomInt(speedMin, speedMax) + Number(intent.speed_bonus ?? intent.speedBonus ?? 0)),
    skill: findBossSkill(skillId),
    requestedName: skillId,
    assignedSinnerId: null,
    assignedQueueIndex: null,
    result: null,
  })).sort((a, b) => b.speed - a.speed || a.index - b.index);
  $("bossSp").value = String(intent.boss_sp ?? intent.bossSp ?? 0);
  $("intentSource").textContent = `${intent.pattern?.label || intent.source} / ${intent.row?.row_id || "row"}`;
  renderBehaviorNotes({
    ...intent,
    bossSp: intent.boss_sp ?? intent.bossSp,
    speedBonus: intent.speed_bonus ?? intent.speedBonus,
    skillIds: slotRefs,
  });
  renderBossSlots();
  renderVisualPlanner();
  renderAssignments();
}

function renderBossSearchResults(items) {
  const root = $("bossResults");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = '<div class="empty">No boss found.</div>';
    return;
  }
  for (const boss of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "result-card";
    button.innerHTML = `<strong>${escapeHtml(boss.name_en || boss.boss_id)}</strong><span>${escapeHtml(boss.boss_id)}</span><small>Lv ${escapeHtml(boss.level)}</small>`;
    button.addEventListener("click", () => loadBoss(boss.boss_id));
    root.appendChild(button);
  }
}

async function searchBoss() {
  const query = $("bossQuery").value.trim();
  $("bossResults").innerHTML = '<div class="empty">Searching...</div>';
  const payload = await getJson(`/bosses/search?q=${encodeURIComponent(query)}&limit=10`);
  renderBossSearchResults(payload.items || []);
}

async function loadBoss(id) {
  const boss = await getJson(`/bosses/${encodeURIComponent(id)}`);
  state.boss = boss;
  state.bossSlots = [];
  $("bossMeta").textContent = `${boss.boss_id} / Lv ${text(boss.level)}`;
  $("bossName").textContent = boss.name_en || boss.boss_id;
  $("bossLocal").textContent = boss.name_th || "No Thai boss name yet.";
  const img = $("bossImage");
  img.src = `/assets/boss/${encodeURIComponent(boss.boss_id)}/image/idle_sprite`;
  img.onerror = () => { img.src = `/assets/boss/${encodeURIComponent(boss.boss_id)}/image/moving_sprite`; };
  generateBossIntent().catch((err) => alert(err.message));
}

function renderBossSlots() {
  const root = $("bossSlots");
  root.classList.remove("empty");
  root.innerHTML = "";
  for (const slot of state.bossSlots) {
    const skill = slot.skill || {};
    const card = document.createElement("article");
    card.className = "boss-slot-card";
    card.innerHTML = `
      <div class="slot-speed">${slot.speed}</div>
      <img class="skill-icon" src="/assets/boss-skill-icon/${encodeURIComponent(state.boss.boss_id)}/${encodeURIComponent(skill.skill_id || "")}" alt="" onerror="this.style.display='none'" />
      <div class="slot-main">
        <div class="slot-kicker">Boss Slot ${slot.index}</div>
        <h4>${escapeHtml(bossSkillName(skill))}</h4>
        <div class="numbers">
          <span>${escapeHtml(coinPowerLine(skill))}</span>
          <span>Weight ${escapeHtml(skill.attack_weight ?? 1)}</span>
          <span>${escapeHtml(text(skill.affinity))} / ${escapeHtml(text(skill.damage_type))}</span>
        </div>
        <div class="effects compact-effects">${formatBossRich(bossEffectText(skill) || "No effect text imported.")}</div>
      </div>
      <label class="assign-select">Clash with <select data-boss-slot="${slot.id}">${sinnerOptions(slot.assignedSinnerId)}</select></label>
    `;
    root.appendChild(card);
  }
  root.querySelectorAll("select[data-boss-slot]").forEach((select) => {
    select.addEventListener("change", (event) => {
      const target = state.bossSlots.find((slot) => slot.id === event.currentTarget.dataset.bossSlot);
      if (target) {
        target.assignedSinnerId = event.currentTarget.value || null;
        target.assignedQueueIndex = null;
      }
      renderVisualPlanner();
      renderAssignments();
    });
  });
}

function sinnerOptions(selected) {
  const options = ['<option value="">Unopposed</option>'];
  for (const sinner of state.sinners) {
    const profileName = sinner.profile?.identity?.english_name || `Sinner ${sinner.id}`;
    const skill = selectedIdentitySkill(sinner);
    const label = `${profileName} - ${identitySkillName(skill)}`;
    options.push(`<option value="${sinner.id}" ${String(selected) === String(sinner.id) ? "selected" : ""}>${escapeHtml(label)}</option>`);
  }
  return options.join("");
}

function addSinner(defaultQuery = "") {
  if (state.sinners.length >= 7) {
    alert("Limbus field limit: 7 ally slots for this planner.");
    return null;
  }
  const id = String(state.nextSinnerId++);
  state.sinners.push({ id, query: defaultQuery, profile: null, queue: [], selectedQueueIndex: 0, useDefense: false });
  renderSinners();
  renderVisualPlanner();
  return id;
}

function removeSinner(id) {
  state.sinners = state.sinners.filter((sinner) => sinner.id !== id);
  for (const slot of state.bossSlots) {
    if (slot.assignedSinnerId === id) {
      slot.assignedSinnerId = null;
      slot.assignedQueueIndex = null;
    }
  }
  if (state.armedSkill?.sinnerId === id) state.armedSkill = null;
  renderSinners();
  renderBossSlots();
  renderVisualPlanner();
  renderAssignments();
}

function attackSkills(profile) {
  return (profile?.skills || []).filter((skill) => /^skill_[123]/i.test(String(skill.slot || "")));
}

function identityDefenseSkill(profile) {
  return (profile?.skills || []).find((skill) => /defense/i.test(String(skill.slot || ""))) || null;
}

function skillDeckCount(skill) {
  if (Number.isFinite(Number(skill?.deck_count))) return Math.max(1, Number(skill.deck_count));
  const slot = String(skill?.slot || "").toLowerCase();
  if (slot.startsWith("skill_1")) return 3;
  if (slot.startsWith("skill_2")) return 2;
  if (slot.startsWith("skill_3")) return 1;
  return 1;
}

function drawSinnerQueue(sinner) {
  const deck = [];
  for (const skill of attackSkills(sinner.profile)) {
    for (let i = 0; i < skillDeckCount(skill); i += 1) deck.push(skillKey(skill));
  }
  const shuffled = [...deck].sort(() => Math.random() - 0.5);
  while (shuffled.length < 3 && deck.length) shuffled.push(...deck);
  sinner.queue = shuffled.slice(0, 3);
  sinner.selectedQueueIndex = 0;
  sinner.useDefense = false;
}

function skillFromQueue(sinner, index) {
  const key = sinner.queue?.[index];
  return (sinner.profile?.skills || []).find((skill) => skillKey(skill) === key) || null;
}

function selectedIdentitySkill(sinner) {
  if (sinner.useDefense) return identityDefenseSkill(sinner.profile) || skillFromQueue(sinner, sinner.selectedQueueIndex);
  return skillFromQueue(sinner, sinner.selectedQueueIndex) || attackSkills(sinner.profile)[0] || null;
}

function selectedSkillForBossSlot(slot, sinner) {
  if (!sinner) return null;
  if (Number.isFinite(Number(slot?.assignedQueueIndex))) {
    return skillFromQueue(sinner, Number(slot.assignedQueueIndex)) || selectedIdentitySkill(sinner);
  }
  return selectedIdentitySkill(sinner);
}

function renderQueueCard(sinner, index, locked = false) {
  const skill = skillFromQueue(sinner, index);
  const selected = Number(sinner.selectedQueueIndex || 0) === index && !locked;
  const armed = state.armedSkill?.sinnerId === sinner.id && Number(state.armedSkill?.queueIndex) === index && !locked;
  const kind = locked ? "next" : "usable";
  if (!skill) return `<button type="button" class="queue-card ${kind} locked" disabled><span>Empty</span></button>`;
  const id = sinner.profile?.identity?.id || "";
  return `
    <button type="button" class="queue-card ${kind} ${selected ? "selected" : ""} ${armed ? "armed" : ""} ${locked ? "locked" : ""}" data-queue-sinner="${sinner.id}" data-queue-index="${index}" data-drag-skill="${sinner.id}:${index}" draggable="${locked ? "false" : "true"}" ${locked ? "disabled" : ""} title="${escapeHtml(identitySkillName(skill))}">
      <span class="queue-speed">${locked ? "?" : index + 1}</span>
      <img src="/assets/skill-icon/${encodeURIComponent(id)}/${encodeURIComponent(skillKey(skill))}?lang=${LANG}&uptie=${UPTIE}" alt="" onerror="this.style.display='none'" />
      <strong>${escapeHtml(identitySkillName(skill))}</strong>
      <small>${escapeHtml(coinPowerLine(skill))}</small>
    </button>
  `;
}

function renderSkillQueue(sinner) {
  if (!sinner.profile) return '<div class="empty">Pick identity to draw skills.</div>';
  if (!sinner.queue?.length) drawSinnerQueue(sinner);
  const defense = identityDefenseSkill(sinner.profile);
  const selectedSkill = selectedIdentitySkill(sinner);
  return `
    <div class="combat-tray">
      <div class="next-rail">
        ${renderQueueCard(sinner, 2, true)}
      </div>
      <div class="usable-rail">
        ${renderQueueCard(sinner, 0)}
        ${renderQueueCard(sinner, 1)}
      </div>
      <div class="tray-readout">
        <span>${sinner.useDefense ? "DEF" : "USE"}</span>
        <strong>${escapeHtml(identitySkillName(selectedSkill))}</strong>
      </div>
    </div>
    ${sinner.useDefense && defense ? `<div class="defense-note">Defense replaces the selected bottom skill: ${escapeHtml(identitySkillName(defense))}</div>` : ""}
  `;
}

function renderSinners() {
  const root = $("sinnerSlots");
  const addButton = $("addSinner");
  if (addButton) addButton.disabled = state.sinners.length >= 7;
  root.innerHTML = "";
  for (const sinner of state.sinners) {
    const card = document.createElement("article");
    card.className = "sinner-card";
    const profile = sinner.profile;
    const skills = profile?.skills || [];
    card.innerHTML = `
      <div class="sinner-head">
        <img class="portrait" ${profile ? `src="/assets/identity-image/${encodeURIComponent(profile.identity.id)}?lang=${LANG}&uptie=${UPTIE}"` : ""} alt="" onerror="this.style.display='none'" />
        <div>
          <strong>${escapeHtml(profile?.identity?.english_name || `Sinner Slot ${sinner.id}`)}</strong>
          <span>${escapeHtml(profile?.localized_identity_name?.th || profile?.localized_personality?.th || "Search identity")}</span>
        </div>
        <button type="button" data-remove-sinner="${sinner.id}">X</button>
      </div>
      <form class="search-row mini-search" data-search-sinner="${sinner.id}">
        <input value="${escapeHtml(sinner.query)}" autocomplete="off" placeholder="regret faust, yi sang..." />
        <button type="submit">Search</button>
      </form>
      <div class="mini-results" data-results-for="${sinner.id}"></div>
      <div class="sinner-picks">
        <label>SP <input data-sp-for="${sinner.id}" type="number" min="-45" max="45" value="45" /></label>
        <button type="button" data-redraw-queue="${sinner.id}" ${profile ? "" : "disabled"}>Draw</button>
        <button type="button" class="defense-toggle ${sinner.useDefense ? "active" : ""}" data-defense-for="${sinner.id}" ${identityDefenseSkill(profile) ? "" : "disabled"}>Defense</button>
      </div>
      <div class="skill-queue" data-queue-for="${sinner.id}">${renderSkillQueue(sinner)}</div>
      <div class="sinner-skill-preview" data-preview-for="${sinner.id}"></div>
    `;
    root.appendChild(card);
  }
  root.querySelectorAll("[data-remove-sinner]").forEach((button) => button.addEventListener("click", () => removeSinner(button.dataset.removeSinner)));
  root.querySelectorAll("form[data-search-sinner]").forEach((form) => form.addEventListener("submit", (event) => {
    event.preventDefault();
    searchSinner(form.dataset.searchSinner, form.querySelector("input").value.trim()).catch((err) => alert(err.message));
  }));
  root.querySelectorAll("[data-queue-sinner]").forEach((button) => button.addEventListener("click", () => {
    const sinner = state.sinners.find((item) => item.id === button.dataset.queueSinner);
    if (!sinner || button.disabled) return;
    const queueIndex = Number(button.dataset.queueIndex || 0);
    sinner.selectedQueueIndex = queueIndex;
    sinner.useDefense = false;
    state.armedSkill = { sinnerId: sinner.id, queueIndex };
    renderSinners();
    renderBossSlots();
    renderVisualPlanner();
    renderAssignments();
  }));
  root.querySelectorAll("[data-redraw-queue]").forEach((button) => button.addEventListener("click", () => {
    const sinner = state.sinners.find((item) => item.id === button.dataset.redrawQueue);
    if (!sinner) return;
    drawSinnerQueue(sinner);
    if (state.armedSkill?.sinnerId === sinner.id) state.armedSkill = null;
    renderSinners();
    renderBossSlots();
    renderVisualPlanner();
    renderAssignments();
  }));
  root.querySelectorAll("[data-defense-for]").forEach((button) => button.addEventListener("click", () => {
    const sinner = state.sinners.find((item) => item.id === button.dataset.defenseFor);
    if (!sinner) return;
    sinner.useDefense = !sinner.useDefense;
    if (sinner.useDefense) state.armedSkill = { sinnerId: sinner.id, queueIndex: sinner.selectedQueueIndex || 0 };
    renderSinners();
    renderBossSlots();
    renderVisualPlanner();
    renderAssignments();
  }));
  root.querySelectorAll("[data-drag-skill]").forEach((button) => {
    button.addEventListener("dragstart", (event) => {
      const [sinnerId, queueIndex] = button.dataset.dragSkill.split(":");
      state.draggingSkill = { sinnerId, queueIndex: Number(queueIndex) };
      state.armedSkill = { sinnerId, queueIndex: Number(queueIndex) };
      event.dataTransfer.setData("text/plain", button.dataset.dragSkill);
      event.dataTransfer.effectAllowed = "link";
      button.classList.add("dragging");
    });
    button.addEventListener("dragend", () => {
      state.draggingSkill = null;
      button.classList.remove("dragging");
      document.querySelectorAll(".visual-anchor.hover").forEach((item) => item.classList.remove("hover"));
    });
  });
  for (const sinner of state.sinners) renderSinnerPreview(sinner.id);
}

async function searchSinner(id, query) {
  const sinner = state.sinners.find((item) => item.id === id);
  if (!sinner || !query) return [];
  sinner.query = query;
  const results = document.querySelector(`[data-results-for="${id}"]`);
  results.innerHTML = '<div class="empty">Searching...</div>';
  const payload = await getJson(`/identities/search?q=${encodeURIComponent(query)}&limit=6`);
  const items = payload.items || [];
  results.innerHTML = items.map((item) => `
    <button type="button" class="mini-result" data-load-identity="${escapeHtml(item.identity_id)}" data-sinner="${id}">
      <strong>${escapeHtml(item.english_name)}</strong><span>${escapeHtml(item.localized_identity_name || item.localized_name || "-")}</span>
    </button>
  `).join("") || '<div class="empty">No identity found.</div>';
  results.querySelectorAll("[data-load-identity]").forEach((button) => button.addEventListener("click", () => loadSinnerIdentity(button.dataset.sinner, button.dataset.loadIdentity)));
  return items;
}

async function loadSinnerIdentity(id, identityId) {
  const sinner = state.sinners.find((item) => item.id === id);
  if (!sinner) return;
  sinner.profile = await getJson(`/identities/${encodeURIComponent(identityId)}?lang=${LANG}&uptie=${UPTIE}`);
  drawSinnerQueue(sinner);
  renderSinners();
  renderBossSlots();
  renderVisualPlanner();
  renderAssignments();
}

function renderSinnerPreview(id) {
  const sinner = state.sinners.find((item) => item.id === id);
  const root = document.querySelector(`[data-preview-for="${id}"]`);
  if (!sinner || !root) return;
  const skill = selectedIdentitySkill(sinner);
  if (!sinner.profile || !skill) {
    root.innerHTML = '<div class="empty">Pick identity and skill.</div>';
    return;
  }
  root.innerHTML = `
    <div class="skill-title-mini">
      <img src="/assets/skill-icon/${encodeURIComponent(sinner.profile.identity.id)}/${encodeURIComponent(skillKey(skill))}?lang=${LANG}&uptie=${UPTIE}" alt="" onerror="this.style.display='none'" />
      <div><strong>${escapeHtml(identitySkillName(skill))}</strong><span>${escapeHtml(coinPowerLine(skill))} / ${escapeHtml(text(skill.affinity))} ${escapeHtml(text(skill.damage_type))}</span></div>
    </div>
    <div class="compact-effects">${formatIdentityRich(skill.localized_description || skill.english_description || "", sinner.profile)}</div>
  `;
}

function headsChance(sp) {
  const clamped = Math.max(-45, Math.min(45, Number(sp || 0)));
  return (50 + clamped) / 100;
}

function rollFixedString(skill, sp) {
  const count = Math.max(0, Number(skill?.coin_count || 0));
  const chance = headsChance(sp);
  const rows = [];
  for (let round = 0; round < 99; round += 1) {
    let row = "";
    for (let coin = 0; coin < Math.max(1, count - round); coin += 1) row += Math.random() < chance ? "H" : "T";
    rows.push(row);
  }
  return rows.join(" ");
}

function manualBossSkill(skill) {
  return {
    skill_id: skill.skill_id,
    name: skill.name_en || skill.name_th || skill.skill_id,
    base_power: Number(skill.base_power || 0),
    coin_power: Number(skill.coin_power || 0),
    coin_count: Number(skill.coin_count || 0),
    coins: Array.from({ length: Math.max(0, Number(skill.coin_count || 0)) }, () => Number(skill.coin_power || 0)),
  };
}


function parseBossOffenseLevel(skill) {
  const match = String(skill?.attack_level_text || "").match(/\d+/);
  return match ? Number(match[0]) : Number(state.boss?.level || state.boss?.defense_level || 0);
}

function resistanceForIdentity(profile, damageType) {
  const key = normalized(damageType);
  const resist = profile?.combat_stats?.resistances || {};
  if (key.includes("slash")) return Number(resist.slash || 1);
  if (key.includes("pierce")) return Number(resist.pierce || 1);
  if (key.includes("blunt")) return Number(resist.blunt || 1);
  return 1;
}

function winnerFinalPower(clashResult, winner) {
  const last = (clashResult?.rounds || [])[Math.max(0, (clashResult?.rounds || []).length - 1)] || {};
  if (winner === "attacker") return Number(last.attacker_power || 0);
  if (winner === "defender") return Number(last.defender_power || 0);
  return 0;
}

async function estimateSlotDamage(slot, clashResult, sinner, sinnerSkill) {
  const winner = clashResult?.winner;
  if (!winner || !["attacker", "defender"].includes(winner)) return null;
  const coinRoll = winnerFinalPower(clashResult, winner);
  if (coinRoll <= 0) return null;
  if (winner === "attacker") {
    const offense = Number(sinnerSkill?.offense_level?.total || sinnerSkill?.offense_level?.base || 0);
    return postJson("/simulate/damage", {
      coin_roll: coinRoll,
      offense_level: offense,
      defense_level: Number(state.boss?.defense_level || state.boss?.body_parts?.[0]?.defense_level || 0),
      damage_type_resistance: 1,
      sin_resistance: 1,
      clash_count: (clashResult.rounds || []).length,
    });
  }
  return postJson("/simulate/damage", {
    coin_roll: coinRoll,
    offense_level: parseBossOffenseLevel(slot.skill),
    defense_level: Number(sinner?.profile?.combat_stats?.defense_level || 0),
    damage_type_resistance: resistanceForIdentity(sinner?.profile, slot.skill?.damage_type_hint || slot.skill?.damage_type),
    sin_resistance: 1,
    clash_count: (clashResult.rounds || []).length,
  });
}

async function runSlotClash(slot) {
  const sinner = state.sinners.find((item) => item.id === slot.assignedSinnerId);
  const skill = selectedSkillForBossSlot(slot, sinner) || selectedIdentitySkill(sinner || {});
  if (!sinner?.profile || !skill || !slot.skill) return null;
  const sinnerSp = Number(document.querySelector(`[data-sp-for="${sinner.id}"]`)?.value || 0);
  const bossSp = Number($("bossSp").value || 0);
  const clashResult = await postJson("/simulate/clash", {
    mode: "sequence",
    uptie: UPTIE,
    attacker: {
      label: sinner.profile.identity.english_name,
      identity_id: sinner.profile.identity.id,
      skill: skillKey(skill),
      uptie: UPTIE,
      sp: sinnerSp,
    },
    defender: {
      label: state.boss.name_en || state.boss.boss_id,
      sp: bossSp,
      manual_skill: manualBossSkill(slot.skill),
    },
    fixed_results: {
      attacker: rollFixedString(skill, sinnerSp),
      defender: rollFixedString(slot.skill, bossSp),
    },
  });
  try {
    clashResult.damage_preview = await estimateSlotDamage(slot, clashResult, sinner, skill);
  } catch (error) {
    clashResult.damage_error = error.message;
  }
  return clashResult;
}

async function runAllClashes() {
  for (const slot of state.bossSlots) {
    slot.result = await runSlotClash(slot);
  }
  renderAssignments();
}

function assignSkillToSlot(slotId, sinnerId, queueIndex = null) {
  const slot = state.bossSlots.find((item) => item.id === slotId);
  const sinner = state.sinners.find((item) => item.id === sinnerId);
  if (!slot || !sinner?.profile) return;
  slot.assignedSinnerId = sinnerId;
  slot.assignedQueueIndex = Number.isFinite(Number(queueIndex)) ? Number(queueIndex) : null;
  if (slot.assignedQueueIndex !== null) {
    sinner.selectedQueueIndex = slot.assignedQueueIndex;
    sinner.useDefense = false;
  }
  slot.result = null;
  state.armedSkill = { sinnerId, queueIndex: Number.isFinite(Number(queueIndex)) ? Number(queueIndex) : sinner.selectedQueueIndex || 0 };
  renderSinners();
  renderBossSlots();
  renderVisualPlanner();
  renderAssignments();
}

function visualBossImageUrl() {
  if (!state.boss) return "";
  return `/assets/boss/${encodeURIComponent(state.boss.boss_id)}/image/idle_sprite`;
}

function visualIdentityImageUrl(profile) {
  if (!profile) return "";
  return `/assets/identity-sprite/${encodeURIComponent(profile.identity.id)}?lang=${LANG}&uptie=${UPTIE}`;
}

function activeSkillName() {
  if (!state.armedSkill) return "Click a usable skill card, then click an enemy anchor.";
  const sinner = state.sinners.find((item) => item.id === state.armedSkill.sinnerId);
  const skill = skillFromQueue(sinner || {}, state.armedSkill.queueIndex) || selectedIdentitySkill(sinner || {});
  return `${sinner?.profile?.identity?.english_name || `Sinner ${state.armedSkill.sinnerId}`} / ${identitySkillName(skill)}`;
}

function renderCommandSkillCard(sinner, index) {
  const skill = skillFromQueue(sinner, index);
  const profile = sinner.profile;
  const armed = state.armedSkill?.sinnerId === sinner.id && Number(state.armedSkill?.queueIndex) === index;
  if (!skill || !profile) return `<button type="button" class="command-skill empty" disabled></button>`;
  return `
    <button type="button" class="command-skill ${armed ? "armed" : ""}" data-command-skill="${sinner.id}:${index}" draggable="true" title="${escapeHtml(identitySkillName(skill))}">
      <img src="/assets/skill-icon/${encodeURIComponent(profile.identity.id)}/${encodeURIComponent(skillKey(skill))}?lang=${LANG}&uptie=${UPTIE}" alt="" onerror="this.style.display='none'" />
      <span>${escapeHtml(coinPowerLine(skill))}</span>
    </button>
  `;
}

function renderCommandPanel() {
  const root = $("visualCommandPanel");
  if (!root) return;
  root.innerHTML = state.sinners.slice(0, 7).map((sinner, index) => {
    const profile = sinner.profile;
    const next = skillFromQueue(sinner, 2);
    const armed = state.armedSkill?.sinnerId === sinner.id;
    return `
      <article class="command-column ${armed ? "armed" : ""}" data-command-sinner="${sinner.id}">
        <div class="next-chip">${next ? `<img src="/assets/skill-icon/${encodeURIComponent(profile.identity.id)}/${encodeURIComponent(skillKey(next))}?lang=${LANG}&uptie=${UPTIE}" alt="" onerror="this.style.display='none'" />` : ""}</div>
        <div class="command-skills">
          ${renderCommandSkillCard(sinner, 0)}
          ${renderCommandSkillCard(sinner, 1)}
        </div>
        <div class="command-portrait">
          <img src="${visualIdentityImageUrl(profile)}" alt="" onerror="this.style.display='none'" />
          <strong>${escapeHtml(profile?.identity?.sinner || profile?.identity?.english_name || `Sinner ${index + 1}`)}</strong>
        </div>
      </article>
    `;
  }).join("");
  root.querySelectorAll("[data-command-skill]").forEach((button) => {
    button.addEventListener("click", () => {
      const [sinnerId, queueIndex] = button.dataset.commandSkill.split(":");
      const sinner = state.sinners.find((item) => item.id === sinnerId);
      if (!sinner) return;
      sinner.selectedQueueIndex = Number(queueIndex);
      sinner.useDefense = false;
      state.armedSkill = { sinnerId, queueIndex: Number(queueIndex) };
      renderSinners();
      renderVisualPlanner();
      renderBossSlots();
      renderAssignments();
    });
    button.addEventListener("dragstart", (event) => {
      const [sinnerId, queueIndex] = button.dataset.commandSkill.split(":");
      state.draggingSkill = { sinnerId, queueIndex: Number(queueIndex) };
      state.armedSkill = { sinnerId, queueIndex: Number(queueIndex) };
      event.dataTransfer.setData("text/plain", button.dataset.commandSkill);
      event.dataTransfer.effectAllowed = "link";
      button.classList.add("dragging");
    });
    button.addEventListener("dragend", () => {
      state.draggingSkill = null;
      button.classList.remove("dragging");
      document.querySelectorAll(".visual-anchor.hover").forEach((item) => item.classList.remove("hover"));
    });
  });
}

function renderVisualPlanner() {
  const allies = $("allyUnits");
  const enemies = $("enemyUnits");
  if (!allies || !enemies) return;
  allies.innerHTML = state.sinners.slice(0, 7).map((sinner, index) => {
    const profile = sinner.profile;
    const armed = state.armedSkill?.sinnerId === sinner.id;
    const queued = state.bossSlots.find((slot) => slot.assignedSinnerId === sinner.id);
    const queuedSkill = queued ? selectedSkillForBossSlot(queued, sinner) : null;
    return `
      <article class="field-ally ${armed ? "armed" : ""} ${queued ? "queued" : ""}" data-visual-sinner="${sinner.id}" style="--slot:${index}">
        ${queuedSkill ? `<div class="queued-skill-token" data-queued-skill="${sinner.id}:${queued.assignedQueueIndex ?? sinner.selectedQueueIndex ?? 0}"><img src="/assets/skill-icon/${encodeURIComponent(profile.identity.id)}/${encodeURIComponent(skillKey(queuedSkill))}?lang=${LANG}&uptie=${UPTIE}" alt="" onerror="this.style.display='none'" /></div>` : ""}
        <div class="field-speed">${7 - index}</div>
        <img class="field-sprite" src="${visualIdentityImageUrl(profile)}" alt="" onerror="this.style.display='none'" />
        <div class="field-hp">${escapeHtml(profile?.combat_stats?.hp || "-")}</div>
      </article>
    `;
  }).join("") || '<div class="empty">Add identities to plan.</div>';
  const anchors = state.bossSlots.map((slot) => {
    const skill = slot.skill || {};
    const sinner = state.sinners.find((item) => item.id === slot.assignedSinnerId);
    const assignedSkill = selectedSkillForBossSlot(slot, sinner) || selectedIdentitySkill(sinner || {});
    return `
      <button type="button" class="visual-anchor ${sinner ? "assigned" : ""}" data-visual-slot="${slot.id}">
        <span>${escapeHtml(slot.speed)}</span>
        <img src="/assets/boss-skill-icon/${encodeURIComponent(state.boss?.boss_id || "")}/${encodeURIComponent(skill.skill_id || "")}" alt="" onerror="this.style.display='none'" />
        <strong>${escapeHtml(bossSkillName(skill))}</strong>
        <small>${sinner ? `${escapeHtml(sinner.profile?.identity?.sinner || `Sinner ${sinner.id}`)} / ${escapeHtml(identitySkillName(assignedSkill))}` : "target"}</small>
      </button>
    `;
  }).join("");
  enemies.innerHTML = `
    <div class="enemy-stage">
      <div class="enemy-anchor-row">${anchors || '<div class="empty">Generate boss intent.</div>'}</div>
      <img class="visual-boss-sprite" src="${visualBossImageUrl()}" alt="" onerror="this.src='/assets/boss/${encodeURIComponent(state.boss?.boss_id || "")}/image/moving_sprite'; this.onerror=null" />
      <div class="visual-boss-name">${escapeHtml(state.boss?.name_en || state.boss?.boss_id || "No boss")}</div>
    </div>
  `;
  const status = document.querySelector(".planner-status");
  if (status) status.textContent = activeSkillName();
  enemies.querySelectorAll("[data-visual-slot]").forEach((anchor) => {
    anchor.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "link";
      anchor.classList.add("hover");
    });
    anchor.addEventListener("dragleave", () => anchor.classList.remove("hover"));
    anchor.addEventListener("drop", (event) => {
      event.preventDefault();
      anchor.classList.remove("hover");
      const raw = event.dataTransfer.getData("text/plain") || "";
      const [sinnerId, queueIndex] = raw.split(":");
      if (sinnerId) assignSkillToSlot(anchor.dataset.visualSlot, sinnerId, Number(queueIndex));
    });
    anchor.addEventListener("click", () => {
      if (state.armedSkill) assignSkillToSlot(anchor.dataset.visualSlot, state.armedSkill.sinnerId, state.armedSkill.queueIndex);
    });
  });
  renderCommandPanel();
  requestAnimationFrame(renderConnectionLines);
}

function renderConnectionLines() {
  const svg = $("connectionLayer");
  const planner = document.querySelector(".visual-planner");
  if (!svg || !planner) return;
  const rect = planner.getBoundingClientRect();
  svg.setAttribute("viewBox", `0 0 ${Math.max(1, rect.width)} ${Math.max(1, rect.height)}`);
  const defs = svg.querySelector("defs")?.outerHTML || "";
  const paths = [];
  for (const slot of state.bossSlots) {
    if (!slot.assignedSinnerId) continue;
    const commandKey = slot.assignedQueueIndex !== null && slot.assignedQueueIndex !== undefined ? `${slot.assignedSinnerId}:${slot.assignedQueueIndex}` : null;
    const from = (commandKey && document.querySelector(`[data-queued-skill="${commandKey}"]`)) || (commandKey && document.querySelector(`[data-command-skill="${commandKey}"]`)) || document.querySelector(`[data-visual-sinner="${slot.assignedSinnerId}"]`);
    const to = document.querySelector(`[data-visual-slot="${slot.id}"]`);
    if (!from || !to) continue;
    const a = from.getBoundingClientRect();
    const b = to.getBoundingClientRect();
    const x1 = a.left + a.width / 2 - rect.left;
    const y1 = a.top + a.height / 2 - rect.top;
    const x2 = b.left + b.width / 2 - rect.left;
    const y2 = b.top + b.height / 2 - rect.top;
    const skyY = Math.max(54, Math.min(y1, y2) - 96);
    paths.push(`<path class="plan-line" d="M ${x1} ${y1} C ${x1} ${skyY}, ${x2} ${skyY}, ${x2} ${y2}" />`);
  }
  svg.innerHTML = defs + paths.join("");
}

function renderAssignments() {
  const root = $("assignmentSummary");
  root.classList.remove("empty");
  if (!state.bossSlots.length) {
    root.classList.add("empty");
    root.textContent = "Generate boss intent.";
    return;
  }
  root.innerHTML = state.bossSlots.map((slot) => {
    const sinner = state.sinners.find((item) => item.id === slot.assignedSinnerId);
    const skill = selectedSkillForBossSlot(slot, sinner) || selectedIdentitySkill(sinner || {});
    const result = slot.result;
    const winnerText = result?.winner === "clash_cancelled" ? "cancelled after 99" : result?.winner;
    const winner = winnerText ? `<strong>${escapeHtml(winnerText)}</strong>` : "not rolled";
    const damage = result?.damage_preview ? `<div class="damage-preview">Damage ${escapeHtml(result.damage_preview.final_damage)} <span>raw ${escapeHtml(Math.round(result.damage_preview.raw_damage * 100) / 100)}</span></div>` : "";
    return `
      <article class="assignment-card">
        <div><b>Speed ${slot.speed}</b> ${escapeHtml(bossSkillName(slot.skill))}</div>
        <div>${sinner?.profile ? `${escapeHtml(sinner.profile.identity.english_name)} / ${escapeHtml(identitySkillName(skill))}` : "Unopposed"}</div>
        <div>${winner}</div>
        ${damage}
      </article>
    `;
  }).join("");
}

$("bossSearch").addEventListener("submit", (event) => {
  event.preventDefault();
  searchBoss().catch((err) => alert(err.message));
});
$("generateIntent").addEventListener("click", () => generateBossIntent().catch((err) => alert(err.message)));
$("addSinner").addEventListener("click", () => addSinner());
$("runAllClashes").addEventListener("click", () => runAllClashes().catch((err) => alert(err.message)));
window.addEventListener("resize", () => renderConnectionLines());

addSinner("nursefather yi sang");
addSinner("regret faust");
$("bossQuery").value = new URLSearchParams(location.search).get("q") || "lei";
searchBoss().then(async () => {
  const items = (await getJson(`/bosses/search?q=${encodeURIComponent($("bossQuery").value)}&limit=1`)).items || [];
  if (items[0]) await loadBoss(items[0].boss_id);
}).catch(() => {});
async function loadFirstSearchResult(slotId, query) {
  const items = await searchSinner(slotId, query);
  if (items[0]?.identity_id) await loadSinnerIdentity(slotId, items[0].identity_id);
}
loadFirstSearchResult("1", "nursefather yi sang").catch(() => {});
loadFirstSearchResult("2", "regret faust").catch(() => {});



