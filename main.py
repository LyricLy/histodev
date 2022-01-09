import asyncio
import discord
import json
import os
import typing
import matplotlib
import matplotlib.pyplot as plt
import itertools

from datetime import datetime
from discord.ext import commands, tasks


COLOURS = ["r", "g", "b", "k"]


intents = discord.Intents(
    guilds=True,
    members=True,
    messages=True,
    presences=True
)

bot = commands.Bot(command_prefix="hd!", intents=intents)
bot.pyplot_lock = asyncio.Lock()
bot.load_extension("jishaku")
with open("data.json") as f:
    data = json.load(f)
with open("hdata.json") as f:
    hdata = json.load(f)
with open("data30.json") as f:
    data30 = json.load(f)


@bot.event
async def on_ready():
    print(f"Ready on {bot.user} (ID {bot.user.id})")

@bot.command()
async def owner(ctx):
    await ctx.send("オーナーはLyricLy#9345です。")

@bot.command(aliases=["histodev30"])
async def histodev(ctx, member: discord.Member = None):
    async with bot.pyplot_lock:
        member = member or ctx.author
        if ctx.invoked_with == "histodev30":
            d30 = data30[str(member.id)]
            d = [[0]*len(d30[0][0]) for _ in range(len(d30[0]))]
            for day in d30:
                for i, hour in enumerate(day):
                    for j, status in enumerate(hour):
                        d[i][j] += status
        else:
            d = data[str(member.id)]
        for i, thing in enumerate(zip(*d)):
            plt.plot([x / tot if (tot := sum(d[j])) else x for j, x in enumerate(thing)], f".-{COLOURS[i]}")
        plt.xlabel("green = desktop, blue = web, red = mobile, black = offline")
        plt.ylabel("proportion")
        plt.xticks(range(24))
        plt.savefig("img.png")
        await ctx.send(file=discord.File("img.png"))
        plt.close()

async def catch_up(ctx):
    last = datetime.utcfromtimestamp(hdata["last"])
    if (datetime.utcnow() - last).total_seconds() > 1200:
        m = await ctx.send("Catching up on history...")
        async with ctx.channel.typing():
            messages = 0
            for i, channel in enumerate(ctx.guild.text_channels):
                try:
                    async for message in channel.history(limit=None, after=last):
                        messages += 1
                        if messages % 1000 == 0:
                            print(f"{messages} messages processed")
                        d = str(matplotlib.dates.date2num(datetime(year=message.created_at.year, month=message.created_at.month, day=1)))
                        try:
                            hdata["users"][str(message.author.id)][d] += 1
                        except KeyError:
                            if str(message.author.id) not in hdata["users"]:
                                hdata["users"][str(message.author.id)] = {}
                            hdata["users"][str(message.author.id)][d] = 1
                except discord.Forbidden:
                    pass
        hdata["last"] = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()
        with open("hdata.json", "w") as f:
            json.dump(hdata, f)
        await m.delete()

@commands.check
def is_in_esolangs(ctx):
    return ctx.guild.id == 346530916832903169

@commands.max_concurrency(1)
@is_in_esolangs
@bot.command()
async def histohist(ctx, *members: typing.Union[discord.Member, int]):
    await catch_up(ctx)
    if -1 in members:
        members = ctx.guild.members
    elif -2 in members:
        members = sorted(ctx.guild.members, key=lambda u: sum(hdata["users"][str(u.id)].values()) if str(u.id) in hdata["users"] else 0, reverse=True)[:10]
    members = ctx.guild.members if -1 in members else members or (ctx.author,)
    NAMES = {
        "b": "blue",
        "g": "green",
        "r": "red",
        "c": "cyan",
        "m": "magenta",
        "y": "yellow",
        "k": "black"
    }
    async with bot.pyplot_lock:
        colours = {}
        for member, c in zip(members, itertools.cycle("bgrcmyk")):
            colours[member] = NAMES[c]
            id = member if isinstance(member, int) else member.id
            try:
                plt.plot_date(*zip(*((float(x), y) for x, y in sorted(hdata["users"][str(id)].items()))), c)
            except KeyError:
                await ctx.send(f"Didn't find `{member}`.")
        if len(members) > 1:
            plt.xlabel(", ".join(f"{c} = {m}" for m, c in colours.items()), fontsize=8, wrap=True)
        plt.ylabel("messages")
        plt.savefig("img.png")
        await ctx.send(file=discord.File("img.png"))
        plt.close()

count = 0

@tasks.loop(minutes=10)
async def get_data():
    global count
    count += 1
    new_day = False
    if count == 144:
        count = 0
        new_day = True

    await bot.wait_until_ready()

    hour = datetime.utcnow().hour
    for member in set(bot.get_all_members()):
        try:
            values = data[str(member.id)][hour]
        except KeyError:
            data[str(member.id)] = [[0, 0, 0, 0] for _ in range(24)]
            values = [0, 0, 0, 0]
        try:
            values30 = data30[str(member.id)][hour]
        except KeyError:
            data30[str(member.id)] = [[[0, 0, 0, 0] for _ in range(24)] for _ in range(30)]
            values30 = [[0, 0, 0, 0] for _ in range(24)]
        if new_day:
            values30.pop(0)
            values30.append([0, 0, 0, 0])
        if member.mobile_status != discord.Status.offline:
            values[0] += 1
            values30[-1][0] += 1
        elif member.desktop_status != discord.Status.offline:
            values[1] += 1
            values30[-1][1] += 1
        elif member.web_status != discord.Status.offline:
            values[2] += 1
            values30[-1][2] += 1
        else:
            values[3] += 1
            values30[-1][3] += 1
        data[str(member.id)][hour] = values
    with open("data.json", "w") as f:
        json.dump(data, f)
    with open("data30.json", "w") as f:
        json.dump(data30, f)


get_data.start()
with open("token.txt") as f:
    bot.run(f.read().strip())
