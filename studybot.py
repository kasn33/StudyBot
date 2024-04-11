import discord
import asyncio
from discord.ext import commands
from discord import app_commands #for slash commands if they ever work
from dataclasses import dataclass

BOT_TOKEN = "MTE3Mzg4NjA3MzQzNzQyOTgyMg.G2ZM8V.a608YbuTui05G6UCLt75KGgy66n60ayyv6EMOE"
CHANNEL_ID = 1227722112404553889
SERVER_ID = 1227721401239343187
intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@dataclass
class Session:
    is_active: bool = False
    start_time: int = 0

bot = commands.Bot(command_prefix="!", intents=intents)
session = Session()


#startup message (console and channel in server)
@bot.event
async def on_ready():
    print("Hello! Study bot is ready!")
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Hello! Study bot is ready!")

########### Study tracker functions ###############

@bot.command()
async def start(ctx):
    if session.is_active:
        await ctx.send("Session already active!")
        return
    session.is_active = True
    session.start_time = ctx.message.created_at.timestamp()
    await ctx.send("Study session started!")

################# Extra functions #################

#say hello
@bot.command()
async def hello(ctx):
    await ctx.send("Hello!")

#add variable amount of numbers
@bot.command()
async def add(ctx, *arr):
    result = 0
    for num in arr:
        result += int(num)
    await ctx.send(f"Result: {result}")

#start bot
bot.run(BOT_TOKEN)











#start of slash command implementation
'''
#to sync slash commands (uses prefix instead of slash)
@bot.command()
async def sync(ctx):
    print("sync command")
    await bot.tree.sync(guild=discord.Object(SERVER_ID))
    await ctx.send('Command tree synced.')

@tree.command(
    name = "hi",
    description = "say hi"
)
async def hi(ctx):
    await ctx.response.send_message("Hi!")
'''