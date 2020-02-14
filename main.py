import asyncio
import discord
import json
import os
import matplotlib.pyplot as plt

from datetime import datetime
from discord.ext import commands, tasks


COLOURS = ["r", "g", "b", "k"]


bot = commands.Bot(command_prefix="hd!")
with open("data.json") as f:
    data = json.load(f)


@bot.event
async def on_ready():
    print(f"Ready on {bot.user} (ID {bot.user.id})")

@bot.command()
async def histodev(ctx, member: discord.Member = None):
    member = member or ctx.author
    for i, thing in enumerate(zip(*data[str(member.id)])):
        tot = sum(data[str(member.id)][i])
        plt.plot([x / tot if tot else x for x in thing], f".-{COLOURS[i]}")
        plt.xticks(range(24))
    plt.savefig("img.png")
    await ctx.send(file=discord.File("img.png"))
    plt.close()

@tasks.loop(minutes=20)
async def get_data():
    await bot.wait_until_ready()

    hour = datetime.utcnow().hour
    for member in bot.guilds[0].members:
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
