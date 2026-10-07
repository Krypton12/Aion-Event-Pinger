import json
import os
import asyncio
from zoneinfo import ZoneInfo
import discord
from discord.ext import tasks, commands
from datetime import datetime, time, timezone, timedelta

# bot zeug
TOKEN = "Token of bot"
CONFIG_PATH = "config.json"

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# config laden und speichern damit nix verloren geht nach neustart
def get_config():
    default_cfg = {"channel": None,"rift": None, "shugo": None, "siege": None}
    if not os.path.exists(CONFIG_PATH) or os.path.getsize(CONFIG_PATH) == 0:
        return default_cfg
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except:
        return default_cfg

def update_config(key,val):
    data = get_config()
    data[key] = val
    with open(CONFIG_PATH, "w") as f:
        json.dump(data,f, indent=2)
BERLIN_TZ = ZoneInfo("Europe/Berlin")
#shugo und rift und siege timers fue jetzt
SHUGO_SCHEDULE = [time(hour=h, minute=0, tzinfo=BERLIN_TZ) for h in range(24)] #jede stunde
RIFT_SCHEDULE = [time(hour=h, minute=0, tzinfo=BERLIN_TZ) for h in [2, 5, 8, 11, 14, 17, 20, 23]] # alle 3 ab 2uhr
SIEGE_SCHEDULE = [time(hour=21, minute=0, tzinfo=BERLIN_TZ)] # 21 uhr alle paar tage

@bot.event
async def on_ready():
    print(f"Logged in: {bot.user}")
    # tasks starten falls noch nicht an
    if not shugo_task.is_running():
        shugo_task.start()
    if not rift_task.is_running():
        rift_task.start()
    if not siege_task.is_running():
        siege_task.start()


#commands für setup

@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx, channel: discord.TextChannel = None):
    ch = channel or ctx.channel
    update_config("channel", ch.id)
    await ctx.send(f"Alert channel set to {ch.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setrift(ctx, role: discord.Role):
    update_config("rift", role.id)
    await ctx.send(f"Rift role updated: **{role.name}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def setshugo(ctx, role: discord.Role):
    update_config("shugo", role.id)
    await ctx.send(f"Shugo role updated: **{role.name}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def setsiege(ctx, role: discord.Role):
    update_config("siege", role.id)
    await ctx.send(f"Siege role updated: **{role.name}**")

# status check ob alles gesetzt ist
@bot.command()
async def status(ctx):
    cfg = get_config()
    ch = f"<#{cfg['channel']}>" if cfg.get("channel") else "Not configured"
    rift = f"<@&{cfg['rift']}>" if cfg.get("rift") else "Not configured"
    shugo = f"<@&{cfg['shugo']}>" if cfg.get("shugo") else "Not configured"
    siege = f"<@&{cfg['siege']}>" if cfg.get("siege") else "Not configured"

    await ctx.send(
        f"**curConfig**\n"
        f"- sendChannel: {ch}\n"
        f"- Rift: {rift}\n"
        f"- Shugo: {shugo}\n"
        f"- Siege: {siege}"
    )


#Nachrichten events

async def send_event_alert(role_key, message):
    cfg = get_config()
    ch_id = cfg.get("channel")
    if not ch_id:
        return
    channel = bot.get_channel(ch_id)
    if not channel:
        return

    role_id = cfg.get(role_key)
    mention = f"<@&{role_id}> " if role_id else ""
    await channel.send(f"{mention}{message}")


@tasks.loop(time=SHUGO_SCHEDULE)
async def shugo_task():
    msg = await send_event_alert(
        "shugo", 
        "**Shugo Festival starting!** :shugolove:  "
    )
    if msg:
        # 10 min warten dann nachricht löschen
        await asyncio.sleep(600)
        try:
            await msg.delete()
        except:
            pass
# rift timer
@tasks.loop(time=RIFT_SCHEDULE)
async def rift_task():
    cfg = get_config()
    ch_id = cfg.get("channel")
    if not ch_id:
        return
    channel = bot.get_channel(ch_id)
    if not channel:
        return

    role_id = cfg.get("rift")
    mention = f"<@&{role_id}> " if role_id else ""

    close_ts = int((datetime.now(BERLIN_TZ) + timedelta(minutes=10)).timestamp())

    await channel.send(
        f"{mention}**Rift opened!**\n :friendewhut: "
        f"Portals closes in: <t:{close_ts}:R> (at <t:{close_ts}:t>)\n"
    )
    # 10 min offen lassen
    await asyncio.sleep(600)
    try:
        await msg.edit(
            content=(
                f"{mention}~~**Rift opened!**~~\n"
                f"**Rift is now closed.** Next opening in 3 hours."
            )
        )
    except:
        pass

    # noch 10 min closed stehen lassen dann erst löschen
    await asyncio.sleep(600)
    try:
        await msg.delete()
    except:
        pass
@tasks.loop(time=SIEGE_SCHEDULE)
async def siege_task():
    # montag,donnerstag, samstag
    if datetime.now(BERLIN_TZ).weekday() in (0, 3, 5):
        await send_event_alert(
            "siege", 
            "**Artifact Siege starting!** :mia_eyes: "
        )
    if msg:
            # 1 stunde warten (3600 sekunden) dann löschen
            await asyncio.sleep(3600)
            try:
                await msg.delete()
            except:
                pass

@shugo_task.before_loop
@rift_task.before_loop
@siege_task.before_loop
async def wait_ready():
    await bot.wait_until_ready()

bot.run(TOKEN)
