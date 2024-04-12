import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import sqlite3

BOT_TOKEN = ""
CHANNEL_ID = 1227722112404553889
SERVER_ID = 1227721401239343187
intents = discord.Intents.all()
client = discord.Client(intents=intents)

bot = commands.Bot(command_prefix="!", intents=intents)

#initialize / connect database
con = sqlite3.connect("hours.db")
cur = con.cursor()


#startup message (console and channel in server)
@bot.event
async def on_ready():
    cur.execute("""CREATE TABLE IF NOT EXISTS studiers(
        user_id INTEGER PRIMARY KEY,
        total_time INTEGER
    );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS sessions(
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        start_time INTEGER,
        is_complete INTEGER DEFAULT 0,
        duration INTEGER,
        activity TEXT,
        FOREIGN KEY (user_id) REFERENCES studiers(user_id)
    );""")
    con.commit()
    print("Study bot is ready!")
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Hello! Study bot is ready!")




########### Study tracker functions ###############

@bot.slash_command(description = "Start your study session")
async def start(ctx):
    user_id = int(ctx.author.id)
    check_studier = cur.execute(f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()
    if not check_studier:
        cur.execute(f"INSERT INTO studiers VALUES (?,?)", (user_id, 0))
    check_session = cur.execute(f"SELECT start_time FROM sessions WHERE user_id = (?) AND is_complete = 0", (user_id,)).fetchone()
    if check_session:
        await ctx.send(f"<@{user_id}> Session already active!")
        return
    start_time = discord.Object(ctx.interaction.id).created_at
    start_timestamp = start_time.timestamp()
    cur.execute(f"INSERT INTO sessions (user_id, start_time) VALUES (?,?)", (user_id, start_timestamp))
    con.commit()

    #display time in readable format
    human_readable_time = (start_time - datetime.timedelta(hours=5)).strftime("%H:%M:%S")
    await ctx.send(f"<@{user_id}> New study session started at {human_readable_time}")


@bot.slash_command(description = "End your study session and say what you did")
async def stop(ctx, activity: str):
    user_id = int(ctx.author.id)
    start_value = cur.execute(f"SELECT start_time FROM sessions WHERE user_id = (?) AND is_complete = 0", (user_id,)).fetchone()
    if not start_value:
        await ctx.send(f"<@{user_id}> You haven't started studying yet!")
        return
    start_time = start_value[0]
    duration = discord.Object(ctx.interaction.id).created_at.timestamp() - start_time
    cur.execute(f"UPDATE sessions SET duration = (?), activity = (?), is_complete = 1 WHERE user_id = (?)", (duration, activity, user_id))
    total_time = cur.execute(f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()[0]
    total_time += duration
    cur.execute(F"UPDATE studiers SET total_time = (?) WHERE user_id = (?)", (total_time, user_id))
    con.commit()

    #display time studied in readable format
    human_readable_duration = str(datetime.timedelta(seconds=duration)).split('.')[0]
    human_readable_total = str(datetime.timedelta(seconds=total_time)).split('.')[0]
    await ctx.send(f"<@{user_id}> You spent {human_readable_duration} studying!\nYour total time for the week is now {human_readable_total}")


@bot.slash_command(description = "Check the time for a user")
async def time(ctx, user: discord.Option(discord.Member, required="True")):
    user_id = user.id
    if(user.nick is None):
        user_name = user.name
    else:
        user_name = user.nick
    time_value = cur.execute(f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()
    if not time_value:
        await ctx.send(f"{user_name} has not started studying this week.")
        return
    time_spent = time_value[0]
    human_readable_time = str(datetime.timedelta(seconds=time_spent)).split('.')[0]
    await ctx.send(f"{user_name} has {human_readable_time} study hours this week!")
    


################# Extra functions #################

#say hello
@bot.slash_command(description = "Say hello")
async def hello(ctx):
    await ctx.send("Hello!")

#add variable amount of numbers
@bot.slash_command(description = "Adds two numbers")
async def add(ctx, first: discord.Option(int), second: discord.Option(int)):
    result = first+second
    await ctx.send(f"Result: {result}")



###start bot
bot.run(BOT_TOKEN)





#to do list
    #function to change hours required and total_time (recognize admin)
    #reminders as people get behind
    #function to reset weekly? make manual or a task
    #add comments to stop (*arr -> string -> other table referencing studier probably)
    #the entire competition tracker
