const state = {
  identityId: null,
  profile: null,
};

const $ = (id) => document.getElementById(id);

function lang() {
  return $("lang").value;
}

function uptie() {
  return $("uptie").value;
}

function text(value, fallback = "-") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

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

function escapeHtml(value) {
  return text(value, "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[ch]);
}

function slotLabel(slot) {
  const raw = text(slot);
  const match = raw.match(/^skill_(\d+)$/);
  if (match) return `Skill ${match[1]}`;
  if (raw === "defense") return "Defense";
  return raw.replace(/_/g, " ");
}

function tokenLabel(profile, token) {
  const asset = profile?.token_assets?.[token] || {};
  const labels = asset.label || {};
  if (lang() === "th" && labels.th) return labels.th;
  return labels.en || token;
}

function tokenImageSrc(profile, token) {
  if (profile?.identity?.id && profile?.token_assets?.[token]?.path) {
    return `/assets/token/${encodeURIComponent(profile.identity.id)}/${encodeURIComponent(token)}?lang=${lang()}&uptie=${uptie()}`;
  }
  return `/assets/status/${encodeURIComponent(token)}`;
}

function formatRich(value, profile = state.profile) {
  const safe = escapeHtml(value);
  return safe.replace(/\[([^\]]+)\]/g, (full, token) => {
    const tag = SKILL_TAGS[token] || LABEL_TAGS[token];
    if (tag) {
      return `<span class="skill-tag" style="--tag-color:${tag[1]}">[${tag[0]}]</span>`;
    }
    const label = escapeHtml(tokenLabel(profile, token));
    const src = tokenImageSrc(profile, token);
    return `<span class="status-token"><img src="${src}" alt="" onerror="this.remove()" /><span>${label}</span></span>`;
  }).replace(/\n/g, "<br />");
}

function coinIcon(profile, coinIndex) {
  return `<img class="coin-effect" src="/assets/coin-effect/${encodeURIComponent(profile.identity.id)}/${coinIndex}?lang=${lang()}&uptie=${uptie()}" alt="Coin ${coinIndex}" onerror="this.replaceWith(document.createTextNode('Coin ${coinIndex}'))" />`;
}

function coinSpacer() {
  return `<span class="coin-effect coin-spacer" aria-hidden="true"></span>`;
}

async function getJson(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message || payload.error || response.statusText);
  }
  return payload;
}

function resultSubtitle(item) {
  const sinnerThai = item.localized_sinner_name || "-";
  return `${sinnerThai} / ${item.sinner} / ID ${item.identity_id}`;
}

function renderResults(items) {
  const root = $("identityResults");
  root.innerHTML = "";
  if (!items.length) {
    root.innerHTML = '<div class="empty">No identity found.</div>';
    return;
  }
  for (const item of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "result-item";
    button.innerHTML = `
      <strong>${text(item.english_name)}</strong>
      <em>${text(item.localized_identity_name || item.localized_name)}</em>
      <span>${resultSubtitle(item)}</span>
    `;
    button.addEventListener("click", () => loadIdentity(item.identity_id));
    root.appendChild(button);
  }
}

function localizedSkillName(skill) {
  return lang() === "th" ? skill.localized_name || skill.name?.en : skill.name?.en || skill.localized_name;
}

function localizedDesc(skill) {
  return lang() === "th"
    ? skill.localized_description || skill.english_description
    : skill.english_description || skill.localized_description;
}

function localizedCoinRows(skill) {
  if (lang() === "th" && skill.localized_coin_texts?.length) {
    return skill.localized_coin_texts.map((row) => ({ coin_index: row.coin_index, text: row.text }));
  }
  return (skill.coin_texts || []).map((row) => ({ coin_index: row.coin_index, text: row.en }));
}

function renderStats(profile) {
  const stats = profile.combat_stats || {};
  const resist = stats.resistances || {};
  const stagger = (stats.stagger_thresholds || [])
    .map((row) => `${text(row.percent)}% (${text(row.hp)} HP)`)
    .join(" / ");
  const sanity = stats.sanity || {};
  const panicType = sanity.panic_type || {};
  const localizedFactors = stats.localized_sanity?.factors || {};
  const sanityIncrease = (localizedFactors.increase || []).map((row) => row.text).filter(Boolean);
  const sanityDecrease = (localizedFactors.decrease || []).map((row) => row.text).filter(Boolean);
  const fallbackSanityIncrease = sanity.factors?.increase || [];
  const fallbackSanityDecrease = sanity.factors?.decrease || [];
  const localizedPanic = stats.localized_sanity?.panic_info;
  const panicLabel = localizedPanic
    ? `${localizedPanic.name || localizedPanic.name_th}: ${localizedPanic.panic || "-"}`
    : (panicType.panic || stats.panic);
  $("identityStats").innerHTML = `
    <div><b>HP</b><span>${text(stats.hp)}</span></div>
    <div><b>DEF</b><span>${text(stats.defense_level)}</span></div>
    <div><b>Slash</b><span>${text(resist.slash)}</span></div>
    <div><b>Pierce</b><span>${text(resist.pierce)}</span></div>
    <div><b>Blunt</b><span>${text(resist.blunt)}</span></div>
    <div class="wide-stat"><b>Stagger</b><span>${text(stagger)}</span></div>
    <div class="wide-stat"><b>Panic</b><span>${text(panicLabel)}</span></div>
    <div class="wide-stat"><b>Sanity +</b><span>${(sanityIncrease.length ? sanityIncrease : fallbackSanityIncrease).map(escapeHtml).join("<br />") || "-"}</span></div>
    <div class="wide-stat"><b>Sanity -</b><span>${(sanityDecrease.length ? sanityDecrease : fallbackSanityDecrease).map(escapeHtml).join("<br />") || "-"}</span></div>
  `;
}

function renderIdentityImage(profile) {
  const img = $("identityPortrait");
  img.style.display = "block";
  img.src = `/assets/identity-image/${encodeURIComponent(profile.identity.id)}?lang=${lang()}&uptie=${uptie()}`;
  img.onerror = () => {
    img.style.display = "none";
  };
}

function offenseLabel(skill) {
  const level = skill.offense_level || {};
  if (level.total == null && level.correction == null) return "Offense -";
  const total = level.total ?? "-";
  const base = level.base ?? "-";
  const corr = Number(level.correction || 0);
  const sign = corr >= 0 ? "+" : "";
  return `Offense ${text(total)} (${text(base)}${sign}${text(corr)})`;
}

function renderSkills(profile) {
  const skills = profile.skills || [];
  $("skillCount").textContent = `${skills.length} rows`;
  $("skills").innerHTML = "";
  for (const skill of skills) {
    const rows = localizedCoinRows(skill);
    let lastCoinIndex = null;
    const coinText = rows.length
      ? rows.map((row) => {
          const marker = row.coin_index === lastCoinIndex ? coinSpacer() : coinIcon(profile, row.coin_index);
          lastCoinIndex = row.coin_index;
          return `<li class="coin-row">${marker}<span>${formatRich(row.text, profile)}</span></li>`;
        }).join("")
      : '<li class="muted">No coin text in this record.</li>';
    const coinPower = Number(skill.coin_power || 0);
    const item = document.createElement("article");
    item.className = "skill";
    item.innerHTML = `
      <div class="skill-main">
        <img class="skill-icon" src="/assets/skill-icon/${encodeURIComponent(profile.identity.id)}/${encodeURIComponent(skill.source_skill_text_id || skill.slot)}?lang=${lang()}&uptie=${uptie()}" alt="" loading="lazy" />
        <div class="skill-copy">
          <div class="skill-name-line">
            <span class="slot">${slotLabel(skill.slot)}</span>
            <h4>${text(localizedSkillName(skill))}</h4>
          </div>
          <div class="skill-numbers">
            <span>Base ${text(skill.base_power)}</span>
            <span>Coin ${coinPower >= 0 ? "+" : ""}${text(skill.coin_power)} x${text(skill.coin_count)}</span>
            <span>Atk Weight ${text(skill.attack_weight)}</span>
            <span>${offenseLabel(skill)}</span>
          </div>
        </div>
      </div>
      <div class="chips">
        <span>${text(skill.affinity)}</span>
        <span>${text(skill.damage_type)}</span>
        <span>${text(skill.skill_type)}</span>
      </div>
      <p>${formatRich(localizedDesc(skill), profile)}</p>
      <ul>${coinText}</ul>
    `;
    item.querySelector(".skill-icon").addEventListener("error", (event) => {
      event.currentTarget.style.display = "none";
    });
    $("skills").appendChild(item);
  }
}

function renderPassives(profile) {
  const passiveData = lang() === "th" ? profile.localized_passives || {} : profile.passives || {};
  const blocks = Object.entries(passiveData);
  const root = $("passives");
  root.className = "passive-list";
  root.innerHTML = "";
  if (!blocks.length) {
    root.className = "passive-list empty";
    root.textContent = "No passives.";
    return;
  }
  for (const [type, passives] of blocks) {
    for (const passive of passives || []) {
      const div = document.createElement("div");
      div.className = "passive";
      div.innerHTML = `
        <span>${type}</span>
        <strong>${text(passive.name?.en || passive.name)}</strong>
        <p>${formatRich(passive.description || passive.en, state.profile)}</p>
      `;
      root.appendChild(div);
    }
  }
}


function renderProfile(profile) {
  state.profile = profile;
  state.identityId = profile.identity.id;
  $("identityId").textContent = `${profile.identity.id} / ${profile.identity.sinner} / Rarity ${profile.identity.rarity}`;
  $("identityName").textContent = profile.identity.english_name;
  const thaiIdentity = profile.localized_identity_name?.th;
  const thaiSinner = profile.localized_personality?.th;
  $("identityLocal").textContent = thaiIdentity || (thaiSinner ? `${thaiSinner} / ${profile.identity.sinner}` : "Thai identity title is not imported yet.");
  renderIdentityImage(profile);
  renderStats(profile);
  renderSkills(profile);
  renderPassives(profile);
  renderCard();
}

function renderCard() {
  if (!state.identityId) return;
  $("cardEmpty").style.display = "none";
  const img = $("identityCard");
  img.style.display = "block";
  img.src = `/assets/identity-card/${encodeURIComponent(state.identityId)}?lang=${lang()}&uptie=${uptie()}&t=${Date.now()}`;
}

async function searchIdentities(query) {
  $("identityResults").innerHTML = '<div class="empty">Searching...</div>';
  const payload = await getJson(`/identities/search?q=${encodeURIComponent(query)}&limit=12`);
  renderResults(payload.items || []);
}

async function loadIdentity(id) {
  const profile = await getJson(`/identities/${encodeURIComponent(id)}?lang=${lang()}&uptie=${uptie()}`);
  renderProfile(profile);
}

async function searchStatus(query) {
  const root = $("statusResult");
  root.className = "status-result empty";
  root.textContent = "Searching...";
  const payload = await getJson(`/status/search?q=${encodeURIComponent(query)}&lang=${lang()}`);
  const item = payload.item;
  root.className = "status-result";
  root.innerHTML = `
    <div class="status-title">
      <img src="/assets/status/${encodeURIComponent(item.status_key)}" alt="" />
      <div>
        <strong>${text(item.name)}</strong>
        <span>${text(item.name_en)} / ${text(item.category)}</span>
      </div>
    </div>
    <p>${formatRich(item.description || item.summary)}</p>
  `;
}

$("identitySearch").addEventListener("submit", (event) => {
  event.preventDefault();
  const query = $("identityQuery").value.trim();
  if (query) searchIdentities(query).catch((err) => alert(err.message));
});

$("statusSearch").addEventListener("submit", (event) => {
  event.preventDefault();
  const query = $("statusQuery").value.trim();
  if (query) searchStatus(query).catch((err) => alert(err.message));
});

$("lang").addEventListener("change", () => {
  if (state.identityId) loadIdentity(state.identityId).catch((err) => alert(err.message));
});

$("uptie").addEventListener("change", () => {
  if (state.identityId) loadIdentity(state.identityId).catch((err) => alert(err.message));
});

$("refreshCard").addEventListener("click", renderCard);

searchIdentities("regret faust")
  .then(() => loadIdentity("10207"))
  .catch(() => {});


