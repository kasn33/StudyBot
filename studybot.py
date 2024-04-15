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
DEFAULT_REQUIRED = 32400 #in seconds (9 hours)
admin_roles = set()

bot = commands.Bot(command_prefix="!", intents=intents)

#initialize / connect database
con = sqlite3.connect("hours.db")
cur = con.cursor()


#startup message (console and channel in server)
@bot.event
async def on_ready():
    cur.execute(f"""CREATE TABLE IF NOT EXISTS studiers(
        user_id INTEGER PRIMARY KEY,
        total_time INTEGER DEFAULT 0,
        required_hours INTEGER DEFAULT {DEFAULT_REQUIRED}
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
    cur.execute("""CREATE TABLE IF NOT EXISTS roles(
        role_id INTEGER PRIMARY KEY,
        purpose TEXT
    );""")
    con.commit()
    load_admin()
    print("Study bot is ready!")
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Hello! Study bot is ready!")




########### Study tracker functions ###############

#start studying session
@bot.slash_command(description = "Start your study session")
async def start(ctx):
    user_id = int(ctx.author.id)
    check_studier = cur.execute(f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()
    if not check_studier:
        cur.execute(f"INSERT INTO studiers (user_id) VALUES (?)", (user_id,))
    check_session = cur.execute(f"SELECT start_time FROM sessions WHERE user_id = (?) AND is_complete = 0", (user_id,)).fetchone()
    if check_session:
        await ctx.respond(f"<@{user_id}> Session already active!")
        return
    start_time = discord.Object(ctx.interaction.id).created_at
    start_timestamp = start_time.timestamp()
    cur.execute(f"INSERT INTO sessions (user_id, start_time) VALUES (?,?)", (user_id, start_timestamp))
    con.commit()

    #display time in readable format
    human_readable_time = (start_time - datetime.timedelta(hours=5)).strftime("%H:%M:%S")
    await ctx.respond(f"<@{user_id}> New study session started at {human_readable_time}")


#stop studying session
@bot.slash_command(description = "End your study session and say what you did")
async def stop(ctx, activity: str):
    user_id = int(ctx.author.id)
    values = cur.execute(f"SELECT start_time, session_id FROM sessions WHERE user_id = (?) AND is_complete = 0", (user_id,)).fetchone()
    if not values:
        await ctx.respond(f"<@{user_id}> You haven't started studying yet!")
        return
    start_time, sid = values
    duration = discord.Object(ctx.interaction.id).created_at.timestamp() - start_time
    cur.execute(f"UPDATE sessions SET duration = (?), activity = (?), is_complete = 1 WHERE session_id = (?)", (duration, activity, sid))
    total_time = cur.execute(f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()[0]
    total_time += duration
    cur.execute(f"UPDATE studiers SET total_time = (?) WHERE user_id = (?)", (total_time, user_id))
    con.commit()

    #display time studied in readable format
    human_readable_duration = str(datetime.timedelta(seconds=duration)).split('.')[0]
    human_readable_total = str(datetime.timedelta(seconds=total_time)).split('.')[0]
    await ctx.respond(f"<@{user_id}> You spent {human_readable_duration} studying!\nYour total time for the week is now {human_readable_total}")


#check how much time a user has spent studying this week
@bot.slash_command(description = "Check the time for a user")
async def time(ctx, user: discord.Option(discord.Member, required="True", description="Who you want to check the hours of (could be you)")):
    user_id = user.id
    if not is_admin(ctx) and user_id != int(ctx.author.id):
        await ctx.respond("You don't have permission to check other people!")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    tup = cur.execute(f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studying this week.")
        return
    time_spent = tup[0]
    human_readable_time = str(datetime.timedelta(seconds=time_spent)).split('.')[0]
    await ctx.respond(f"{user_name} has {human_readable_time} study hours this week!")

#show all sessions for a user (need permission if not that user)
@bot.slash_command(description = "Show all of a user's activity for the week")
async def getreport(ctx, user: discord.Option(discord.Member, required="True", description="Who you want to check the activity of (could be you)")):
    user_id = user.id
    if not is_admin(ctx) and user_id != int(ctx.author.id):
        await ctx.respond("You don't have permission to check other people!")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    
    embed = discord.Embed(
        title=f"**Report for {user_name}**",
        color=discord.Colour.blurple(),
    )
    tup = cur.execute("SELECT total_time, required_hours FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studing this week")
        return
    total_time, required_hours = tup
    embed.add_field(name="**Total Activity**", value=f"{user_name} has completed **{str(datetime.timedelta(seconds=total_time)).split('.')[0]}** out of **{str(datetime.timedelta(seconds=required_hours)).split('.')[0]}**")
    sessions = cur.execute(f"SELECT start_time, duration, activity FROM sessions WHERE user_id = (?) AND is_complete = 1 ORDER BY start_time", (user_id,)).fetchall()
    for tup in sessions:
        weekday = (datetime.datetime.fromtimestamp(tup[0])).strftime("%A")
        embed.add_field(name=f"**{weekday}**", value=f"Spent **{str(datetime.timedelta(seconds=tup[1])).split('.')[0]}** doing: {tup[2]}", inline=False)
    await ctx.respond(embed=embed)


#remove time from a user (needs permission) (less than 24 hours)
@bot.slash_command(description = "Add time to somebody (less than 24 hours)")
async def add(ctx, user: discord.Option(discord.Member, required="True", description="Who you want to add time to (could be you)"), hours: discord.Option(int), minutes: discord.Option(int)):
    if not is_admin(ctx):
            await ctx.respond("You don't have permission for this command")
            return
    user_id = user.id
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    tup = cur.execute(f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studying this week.")
        return
    orig_time = tup[0]
    duration = datetime.timedelta(hours=hours, minutes=minutes).seconds
    new_time = orig_time + duration
    cur.execute(f"UPDATE studiers SET total_time = (?) WHERE user_id = (?)", (new_time, user_id))
    current_time = discord.Object(ctx.interaction.id).created_at.timestamp()
    cur.execute(f"INSERT INTO sessions (start_time, is_complete, user_id, duration, activity) VALUES (?,?,?,?,?)", (current_time, 1, user_id, duration, "Added by admin"))
    con.commit()

    human_readable_orig = str(datetime.timedelta(seconds=orig_time)).split('.')[0]
    human_readable_new = str(datetime.timedelta(seconds=new_time)).split('.')[0]
    await ctx.respond(f"Changed hours for {user_name} from {human_readable_orig} to {human_readable_new}")


#add time to a user (needs permission) (less than 24 hours)
@bot.slash_command(description = "Remove time from somebody (less than 24 hours)")
async def subtract(ctx, user: discord.Option(discord.Member, required="True", description="Who you want to remove time from (could be you)"), hours: discord.Option(int), minutes: discord.Option(int)):
    if not is_admin(ctx):
        await ctx.respond("You don't have permission for this command")
        return
    user_id = user.id
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    tup = cur.execute(f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studying this week.")
        return
    orig_time = tup[0]
    duration = datetime.timedelta(hours=hours, minutes=minutes).seconds
    new_time = orig_time - duration
    cur.execute(f"UPDATE studiers SET total_time = (?) WHERE user_id = (?)", (new_time, user_id))
    current_time = discord.Object(ctx.interaction.id).created_at.timestamp()
    cur.execute(f"INSERT INTO sessions (start_time, is_complete, user_id, duration, activity) VALUES (?,?,?,?,?)", (current_time, 1, user_id, duration*(-1), "Removed by admin"))
    con.commit()

    human_readable_orig = str(datetime.timedelta(seconds=orig_time)).split('.')[0]
    human_readable_new = str(datetime.timedelta(seconds=new_time)).split('.')[0]
    await ctx.respond(f"Changed hours for {user_name} from {human_readable_orig} to {human_readable_new}")


#add role for admin (must be server administrator)
@bot.slash_command(description = "Add admin permissions to a role (must be server admin)")
async def promote(ctx, role: discord.Option(discord.Role, required="True", description="Which role do you want to give admin permissions to")):
    if not is_admin(ctx) and not ctx.author.guild_permissions.administrator:
        await ctx.respond("You don't have permission for this command")
        return
    if role.id in admin_roles:
        await ctx.respond("Role is already admin")
        return
    cur.execute(f"INSERT INTO roles (role_id, purpose) VALUES (?, ?)", (role.id, "ADMIN"))
    con .commit()
    admin_roles.add(role.id)
    await ctx.respond(f"Added role {role.name} as admin")


#remove role for admin (must be server administrator)
@bot.slash_command(description = "Remove admin permissions to a role (must be server admin)")
async def demote(ctx, role: discord.Option(discord.Role, required="True", description="Which role do you want to take admin permissions from")):
    if not is_admin(ctx) and not ctx.author.guild_permissions.administrator:
        await ctx.respond("You don't have permission for this command")
        return
    if role.id not in admin_roles:
        await ctx.respond("Role is already not admin")
        return
    cur.execute(f"DELETE FROM roles WHERE role_id = (?) AND purpose = (?)", (role.id, "ADMIN"))
    con.commit()
    admin_roles.remove(role.id)
    await ctx.respond(f"Removed admin permissions for {role.name}")


#clear all the data to start a fresh week
@bot.slash_command(description = "Clear all data for the week (BE CAREFUL)")
async def clear(ctx, sure: discord.Option(str, description="Type \"Yes I am sure\" if you're sure")):
    if not is_admin(ctx):
        await ctx.respond("You don't have permission for this command")
        return
    if sure != "Yes I am sure":
        await ctx.respond("Make sure you're sure")
        return
    cur.execute(f"UPDATE studiers SET total_time = 0")
    cur.execute(f"DELETE FROM sessions")
    con.commit()
    await ctx.respond("Weekly data reset!")
    

#list current active sessions
@bot.slash_command(description = "Show all live sessions")
async def activesessions(ctx):
    if not is_admin(ctx):
        await ctx.respond("You don't have permission for this command")
        return
    sessions = cur.execute("SELECT user_id, start_time FROM sessions WHERE is_complete = 0").fetchall()
    embed = discord.Embed(title="Active Sessions", color=discord.Colour.blurple())
    for session in sessions:
        user = bot.get_user(session[0])
        if user.display_name is None:
            user_name = user.name
        else:
            user_name = user.display_name
        human_readable_time = (datetime.datetime.fromtimestamp(session[1])).strftime("%A, %H:%M:%S")
        embed.add_field(name=f"**{user_name}**",value=f"Active since {human_readable_time}")
    await ctx.respond(embed=embed)


#list all users by if they've completed their hours TODO test
@bot.slash_command(description = "Show time for all server members with required hours")
async def serverreport(ctx):
    if not is_admin(ctx):
        await ctx.respond("You don't have permission for this command")
        return
    embed = discord.Embed(title="Full Report")
    complete, partial, none, never = list()
    for member in server.members:
        if member.nick is None:
            user_name = member.name
        else:
            user_name = member.nick
        tup = cur.execute("SELECT total_time, required_hours FROM studiers WHERE user_id = (?)", (member.id)).fetchone()
        if not tup:
            never.add(member)
        elif tup[0] == 0:
            none.add([member, tup[0], tup[1]])
        elif tup[0] < tup[1]:
            partial.add([member, tup[0], tup[1]])
        else:
            complete.add([member, tup[0], tup[1]])
    
    embed.add_field(name="**Members who completed their hours:**", value="", inline=False)
    for tup in complete:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split('.')[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split('.')[0]
        embed.add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}")
    embed.add_field(name="\n\n**Members who completed only some of their hours:**", value="", inline=False)
    for tup in partial:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split('.')[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split('.')[0]
        embed.add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
    embed.add_field(name="\n\n**Members who completed none of their hours:**", value="", inline=False)
    for tup in none:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split('.')[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split('.')[0]
        embed.add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
    embed.add_field(name="\n\n**Members who have never studied:**", value="", inline=False)
    for member in never:
        if member.nick is None:
            user_name = member.name
        else:
            user_name = member.nick
        embed.add_field(name=f"{user_name}", value="", inline=False)
    await ctx.respond(embed=embed)


#set required hours for user TODO test
@bot.slash_command(description = "Set required hours for a user")
async def setrequired(ctx, user: discord.Option(discord.Member, required="True", description="Which role do you want to give admin permissions to"), hours: discord.Option(int, required="True", description="How many hours per week")):
    user_id = user.id
    if not is_admin(ctx):
        await ctx.respond("You don't have permission for this command")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    cur.execute("UPDATE studiers SET required_hours = (?) WHERE user_id = (?)", (hours, user_id))
    con.commit()
    ctx.respond(f"{user_name} now needs {hours} hours per week!")



################# Extra functions and helpers #################

#say hello
@bot.slash_command(description = "Say hello")
async def hello(ctx):
    await ctx.respond("Hello!")

#return bool for if user has admin permissions
def is_admin(ctx):
    for role in ctx.author.roles:
        if role.id in admin_roles:
            return True
    return False

#load admin list from database
def load_admin():
    admin_tups = cur.execute(f"SELECT role_id FROM roles WHERE purpose = \"ADMIN\"").fetchall()
    for tup in admin_tups:
        admin_roles.add(tup[0])




###start bot
bot.run(BOT_TOKEN)





#to do list
    #daily routine - ping people who are behind, clear at end of week, call report weekly
    #the entire competition tracker
