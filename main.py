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


bot = commands.Bot(command_prefix="hd!")
bot.load_extension("jishaku")
with open("data.json") as f:
    data = json.load(f)
with open("hdata.json") as f:
    hdata = json.load(f)


@bot.event
async def on_ready():
    print(f"Ready on {bot.user} (ID {bot.user.id})")

@bot.command()
async def owner(ctx):
    await ctx.send("owner wa LyricLy#5695 da yo")

@bot.command()
async def histodev(ctx, member: discord.Member = None):
    member = member or ctx.author
    for i, thing in enumerate(zip(*data[str(member.id)])):
        plt.plot([x / tot if (tot := sum(data[str(member.id)][j])) else x for j, x in enumerate(thing)], f".-{COLOURS[i]}")
        plt.xlabel("green = desktop, blue = web, red = mobile")
        plt.ylabel("percentage")
        plt.xticks(range(24))
    plt.savefig("img.png")
    await ctx.send(file=discord.File("img.png"))
    plt.close()

@commands.max_concurrency(1)
@bot.command()
async def histohist(ctx, *members: typing.Union[discord.Member, int]):
    members = members or (ctx.author,)
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

    NAMES = {
        "b": "blue",
        "g": "green",
        "r": "red",
        "c": "cyan",
        "m": "magenta",
        "y": "yellow",
        "k": "black",
        "w": "white"
    }
    colours = {}
    for member, c in zip(members, "bgrcmykw"):
        colours[member] = NAMES[c]
        id = member if isinstance(member, int) else member.id
        try:
            plt.plot_date(*zip(*((float(x), y) for x, y in sorted(hdata["users"][str(id)].items()))), c)
        except KeyError:
            await ctx.send(f"Didn't find `{member}`.")
    if len(members) > 1:
        plt.xlabel(", ".join(f"{c} = {m}" for m, c in colours.items()))
    plt.ylabel("messages")
    plt.savefig("img.png")
    await ctx.send(file=discord.File("img.png"))
    plt.close()

@tasks.loop(minutes=10)
async def get_data():
    await bot.wait_until_ready()

    hour = datetime.utcnow().hour
    for member in set(bot.get_all_members()):
        try:
            values = data[str(member.id)][hour]
        except KeyError:
            data[str(member.id)] = [[0, 0, 0, 0] for _ in range(24)]
            values = [0, 0, 0, 0]
        if not member.mobile_status == discord.Status.offline:
            values[0] += 1
        elif not member.desktop_status == discord.Status.offline:
            values[1] += 1
        elif not member.web_status == discord.Status.offline:
            values[2] += 1
        else:
            values[3] += 1
        data[str(member.id)][hour] = values
    with open("data.json", "w") as f:
        json.dump(data, f)


get_data.start()
with open("token.txt") as f:
    bot.run(f.read().strip())
