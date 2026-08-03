from __future__ import annotations

import os
import sys
from pathlib import Path

import discord
from discord import app_commands


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = ROOT / "work"
if str(WORK_DIR) not in sys.path:
    sys.path.insert(0, str(WORK_DIR))

from build_identity_profile import build_payload  # noqa: E402
from render_identity_card import render_identity_card  # noqa: E402


DEFAULT_UPTIE = 4


def clean_text(value: str | None, limit: int = 900) -> str:
    value = (value or "-").replace('<style="highlight">', "").replace("</style>", "")
    replacements = {
        "[WhenUse]": "[On Use]",
        "[BeforeAttack]": "[Before Attack]",
        "[WinDuel]": "[Clash Win]",
        "[DefeatDuel]": "[Clash Lose]",
        "[OnSucceedAttack]": "[On Hit]",
        "[OnSucceedAttackHead]": "[Heads Hit]",
        "[OnSucceedAttackTail]": "[Tails Hit]",
        "[CriticalOnSucceedAttack]": "[On Crit]",
        "[CriticalActivated]": "[On Crit]",
        "[CantDuel]": "[Unclashable]",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def coin_line(skill: dict) -> str:
    mechanics = skill.get("combat_mechanics") or {}
    coins = mechanics.get("coins") or []
    powers = [coin.get("power") for coin in coins if coin.get("power") is not None]
    if not powers:
        count = int(skill.get("coin_count") or 0)
        powers = [skill.get("coin_power")] * count
    powers_text = " ".join(f"{power:+}" for power in powers if power is not None)
    return f"base {skill.get('base_power')} {powers_text}".strip()


def skill_field(skill: dict, lang: str) -> tuple[str, str]:
    en_name = (skill.get("name") or {}).get("en") or "-"
    th_name = skill.get("localized_name") or en_name
    name = th_name if lang == "th" else en_name
    desc = skill.get("localized_description") if lang == "th" else skill.get("english_description")
    slot = (skill.get("slot") or "").replace("_", " ").title()
    title = f"{slot}: {name}"
    body = (
        f"{skill.get('affinity')} {skill.get('damage_type')} | Coins {coin_line(skill)} | "
        f"Weight {skill.get('attack_weight')}\n"
        f"{clean_text(desc)}"
    )
    return title, body


def build_identity_embed(query: str, lang: str, uptie: int) -> tuple[discord.Embed, Path]:
    payload = build_payload(query, ROOT / "data", uptie, lang)
    identity = payload.get("identity") or {}
    card_path = render_identity_card(query, ROOT / "data", uptie, lang)

    embed = discord.Embed(
        title=identity.get("english_name") or query,
        description=f"{identity.get('sinner')} | Rarity {identity.get('rarity')} | UT{uptie}",
        color=discord.Color.from_rgb(184, 144, 84),
    )
    embed.set_image(url=f"attachment://{card_path.name}")
    embed.set_footer(text="Limbus Assistant prototype")
    return embed, card_path

class LimbusBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


bot = LimbusBot()


@bot.tree.command(name="identity", description="Show a Limbus Company Identity.")
@app_commands.describe(
    name="Identity name, for example Blade Lineage Salsu Faust",
    lang="Display language",
    uptie="Uptie level",
)
@app_commands.choices(
    lang=[
        app_commands.Choice(name="Thai", value="th"),
        app_commands.Choice(name="English", value="en"),
    ]
)
async def identity_command(
    interaction: discord.Interaction,
    name: str,
    lang: app_commands.Choice[str] | None = None,
    uptie: int = DEFAULT_UPTIE,
) -> None:
    await interaction.response.defer()
    chosen_lang = lang.value if lang else "th"
    try:
        embed, card_path = build_identity_embed(name, chosen_lang, uptie)
    except Exception as exc:
        await interaction.followup.send(f"Could not find identity: `{name}`\n`{exc}`", ephemeral=True)
        return

    if image_path:
        await interaction.followup.send(embed=embed, file=discord.File(image_path))
    else:
        await interaction.followup.send(embed=embed)


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Set DISCORD_TOKEN before running the bot.")
    bot.run(token)


if __name__ == "__main__":
    main()

