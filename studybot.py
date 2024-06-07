#version TODO
#contact Kyle Seifert AΨ722 somehow if this isn't me and you have questions or something
#IF YOU HELP WITH THIS BOT YOU CAN TALK ABOUT IT IN INTERVIEWS
#need pycord (might have to mess around with downloads because I did too and idk exactly what fixed it) and also python obviously
#there are functions to set and load things like roles, but for specific stuff like default required hours and channel IDs change the value in the code here at the top
# ^ same goes for things like help menu mentioning specific "Study hours" channel

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
admin_roles, studier_roles, review_roles = set(), set(), set()

bot = commands.Bot(command_prefix="!", intents=intents) # old but maybe useful

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
        purp_id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_id INTEGER,
        purpose TEXT
    );""")
    con.commit()
    load_admin()
    load_studiers()
    load_review()
    print("Study bot is ready!")
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Hello! Study bot is ready!")




###################################### Study tracker functions ######################################

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
    start_time = discord.Object(ctx.interaction.id).created_at - datetime.timedelta(hours=5)
    start_timestamp = start_time.timestamp()
    cur.execute(f"INSERT INTO sessions (user_id, start_time) VALUES (?,?)", (user_id, start_timestamp))
    con.commit()

    #TODO check if user is on academic review and start checker routine if they are

    #display time in readable format
    human_readable_time = start_time.strftime("%H:%M:%S")
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
    duration = (discord.Object(ctx.interaction.id).created_at - datetime.timedelta(hours=5)).timestamp() - start_time
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
    if not is_admin(ctx.author) and user_id != int(ctx.author.id):
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


#check how much time a user has spent studying the previous week
@bot.slash_command(description = "Check the time for a user last week")
async def prev_time(ctx, user: discord.Option(discord.Member, required="True", description="Who you want to check the hours of (could be you)")):
    user_id = user.id
    if not is_admin(ctx.author) and user_id != int(ctx.author.id):
        await ctx.respond("You don't have permission to check other people!")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    tup = cur.execute(f"SELECT total_time FROM prevstudiers WHERE user_id = (?)", (user_id,)).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} did not start studying last week.")
        return
    time_spent = tup[0]
    human_readable_time = str(datetime.timedelta(seconds=time_spent)).split('.')[0]
    await ctx.respond(f"{user_name} has {human_readable_time} study hours this week!")


#show all sessions for a user (need permission if not that user) (won't work if over 25 sessions but there aint no way)
@bot.slash_command(description = "Show all of a user's activity for the week")
async def getreport(ctx, user: discord.Option(discord.Member, required="True", description="Who you want to check the activity of (could be you)")):
    user_id = user.id
    if not is_admin(ctx.author) and user_id != int(ctx.author.id):
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
        readable_time = (datetime.datetime.fromtimestamp(tup[0])+datetime.timedelta(hours=5)).strftime("**%A** starting at %H:%M")
        embed.add_field(name=f"{readable_time}", value=f"Spent **{str(datetime.timedelta(seconds=tup[1])).split('.')[0]}** doing: {tup[2]}", inline=False)
    await ctx.respond(embed=embed)


#show all sessions for a user for the previous week (need permission if not that user)
@bot.slash_command(description = "Show all of a user's activity for the previous week")
async def prev_getreport(ctx, user: discord.Option(discord.Member, required="True", description="Who you want to check the activity of (could be you)")):
    user_id = user.id
    if not is_admin(ctx.author) and user_id != int(ctx.author.id):
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
    tup = cur.execute("SELECT total_time, required_hours FROM prevstudiers WHERE user_id = (?)", (user_id,)).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studing this week")
        return
    total_time, required_hours = tup
    embed.add_field(name="**Total Activity**", value=f"{user_name} has completed **{str(datetime.timedelta(seconds=total_time)).split('.')[0]}** out of **{str(datetime.timedelta(seconds=required_hours)).split('.')[0]}**")
    sessions = cur.execute(f"SELECT start_time, duration, activity FROM prevsessions WHERE user_id = (?) AND is_complete = 1 ORDER BY start_time", (user_id,)).fetchall()
    for tup in sessions:
        readable_time = (datetime.datetime.fromtimestamp(tup[0])+datetime.timedelta(hours=5)).strftime("**%A** starting at %H:%M")
        embed.add_field(name=f"{readable_time}", value=f"Spent **{str(datetime.timedelta(seconds=tup[1])).split('.')[0]}** doing: {tup[2]}", inline=False)
    await ctx.respond(embed=embed)


#remove time from a user (needs permission) (less than 24 hours)
@bot.slash_command(description = "Add time to somebody (less than 24 hours)")
async def add(ctx, user: discord.Option(discord.Member, required="True", description="Who you want to add time to (could be you)"), hours: discord.Option(int), minutes: discord.Option(int)):
    if not is_admin(ctx.author):
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
    if hours<0 or minutes<0:
        await ctx.respond(f"<@{int(ctx.author.id)}> nice try!")
        return
    user_id = user.id
    if not is_admin(ctx.author) and user_id != int(ctx.author.id):
        await ctx.respond("You don't have permission for this command")
        return
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
    if new_time < 0:
        await ctx.respond("Cannot set total time negative!")
        return
    cur.execute(f"UPDATE studiers SET total_time = (?) WHERE user_id = (?)", (new_time, user_id))
    current_time = discord.Object(ctx.interaction.id).created_at.timestamp()
    cur.execute(f"INSERT INTO sessions (start_time, is_complete, user_id, duration, activity) VALUES (?,?,?,?,?)", (current_time, 1, user_id, duration*(-1), "Removed by admin"))
    con.commit()

    human_readable_orig = str(datetime.timedelta(seconds=orig_time)).split('.')[0]
    human_readable_new = str(datetime.timedelta(seconds=new_time)).split('.')[0]
    await ctx.respond(f"Changed hours for {user_name} from {human_readable_orig} to {human_readable_new}")


#add role for admin (must be server administrator)
@bot.slash_command(description = "Add admin permissions to a role (must be server admin)")
async def promote(ctx, perm: discord.Option(str, choices=["Studier", "Admin", "Academic Review"], required="True", description = "What type of \'permission\' do you want to give this role?" ), role: discord.Option(discord.Role, required="True", description="Which role do you want to give admin permissions to")):
    if not is_admin(ctx.author) and not ctx.author.guild_permissions.administrator:
        await ctx.respond("You don't have permission for this command")
        return
    if perm == "Studier":
        if role.id in studier_roles:
            await ctx.respond(f"Role {role.name} is already a studier")
            return
        studier_roles.add(role.id)
        await ctx.respond(f"Added role {role.name} as studier")
    elif perm == "Admin":
        if role.id in admin_roles:
            await ctx.respond(f"Role {role.name} is already admin")
            return
        admin_roles.add(role.id)
        await ctx.respond(f"Added role {role.name} as admin")
    elif perm == "Academic Review":
        if role.id in review_roles:
            await ctx.respond(f"Role {role.name} is already under academic review")
            return
        review_roles.add(role.id)
        await ctx.respond(f"Added role {role.name} as under academic review")
    cur.execute(f"INSERT INTO roles (role_id, purpose) VALUES (?, ?)", (role.id, perm))
    con.commit()
    


#remove role for admin (must be server administrator)
@bot.slash_command(description = "Remove admin permissions to a role (must be server admin)")
async def demote(ctx, perm: discord.Option(str, choices=["Studier", "Admin", "Academic Review"], required="True", description = "What type of \'permission\' do you want to remove from this role?" ), role: discord.Option(discord.Role, required="True", description="Which role do you want to take admin permissions from")):
    if not is_admin(ctx.author) and not ctx.author.guild_permissions.administrator:
        await ctx.respond("You don't have permission for this command")
        return
    if perm == "Studier":
        if role.id not in studier_roles:
            await ctx.respond(f"Role {role.name} is already not a studier")
            return
        studier_roles.remove(role.id)
        await ctx.respond(f"Removed role {role.name} as studier")
    elif perm == "Admin":
        if role.id in admin_roles:
            await ctx.respond(f"Role {role.name} is already not an admin")
            return
        admin_roles.remove(role.id)
        await ctx.respond(f"Removed role {role.name} as admin")
    elif perm == "Academic Review":
        if role.id in review_roles:
            await ctx.respond(f"Role {role.name} is already not under academic review")
            return
        review_roles.remove(role.id)
        await ctx.respond(f"Removed role {role.name} as under academic review")
    cur.execute("DELETE FROM roles WHERE role_id = (?) AND purpose = (?)", (role.id, perm))
    con.commit()


#clear all the data to start a fresh week
@bot.slash_command(description = "Clear all data for the week (BE CAREFUL)")
async def clear(ctx, confirmation: discord.Option(str, description="Type \"Yes I am sure\" if you're sure")):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if confirmation != "Yes I am sure":
        await ctx.respond("Make sure you're sure")
        return
    cur.execute("DROP TABLE prevstudiers")
    cur.execute("DROP TABLE prevsessions")
    cur.execute("CREATE TABLE IF NOT EXISTS prevstudiers AS SELECT * FROM studiers")
    cur.execute("CREATE TABLE IF NOT EXISTS prevsessions AS SELECT * FROM sessions")
    cur.execute("UPDATE studiers SET total_time = 0")
    cur.execute("DELETE FROM sessions")
    con.commit()
    await ctx.respond("Weekly data reset!")
    

#list current active sessions (embeds have a limit so does not scale past 25 - should never be an issue)
@bot.slash_command(description = "Show all live sessions")
async def activesessions(ctx):
    if not is_admin(ctx.author):
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


#list overdue sessions from past week (allow admin to add based on it or whatever is needed) (embeds have a limit so does not scale past 25 - should never be an issue)
@bot.slash_command(description = "Show suspended sessions from previous week")
async def prev_activesessions(ctx):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    sessions = cur.execute("SELECT user_id, start_time FROM prevsessions WHERE is_complete = 0").fetchall()
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


#list all users by if they've completed their hours (and how many of their required hours are done)
@bot.slash_command(description = "Show time for all server members with required hours")
async def serverreport(ctx):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    complete, partial, none, never = list(), list(), list(), list()
    guild = ctx.guild
    members = await guild.fetch_members(limit=None).flatten()
    nicknames = set() # used to verify uniqueness of names (so there can't be 10 people named Steve)
    for member in members:
        if member.nick is not None and is_studier(member):
            nicknames.add(member.nick)   
    for member in members:
        if not is_studier(member):
            continue
        if member.nick is None or list(map(lambda x: x.nick, members)).count(member.nick) > 1:
            user_name = member.name
        else:
            user_name = member.nick
        tup = cur.execute("SELECT total_time, required_hours FROM studiers WHERE user_id = (?)", (member.id,)).fetchone()
        if not tup or tup[0] ==0:
            none.append(member)
        elif tup[0] < tup[1]:
            partial.append([member, tup[0], tup[1]])
        else:
            complete.append([member, tup[0], tup[1]])
    
    embeds=list()
    
    embeds.append(discord.Embed(title="**Members who completed all of their hours**", color=discord.Colour.blurple()))
    fields=1
    for tup in complete:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split('.')[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split('.')[0]
        if fields%25 != 0:
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
        fields+=1
    
    embeds.append(discord.Embed(title="**Members who completed only some of their hours**", color=discord.Colour.blurple()))
    fields=1
    for tup in partial:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split('.')[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split('.')[0]
        if fields%25 != 0:
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
        fields+=1
    
    embeds.append(discord.Embed(title="**Members who completed none of their hours**", color=discord.Colour.blurple()))
    fields=1
    for member in none:
        if member.nick is None:
            user_name = member.name
        else:
            user_name = member.nick
        if fields%25 != 0:
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"", inline=False)
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"", inline=False)
        fields+=1
    
    for embed in embeds:
        await ctx.respond(embed=embed)


#list all users by if they've completed their hours last week (and how many of their required hours are done)
@bot.slash_command(description = "Show previous week time for all server members with required hours")
async def prev_serverreport(ctx):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    complete, partial, none, never = list(), list(), list(), list()
    guild = ctx.guild
    members = await guild.fetch_members(limit=None).flatten()
    nicknames = set() # used to verify uniqueness of names (so there can't be 10 people named Steve)
    for member in members:
        if member.nick is not None and is_studier(member):
            nicknames.add(member.nick)   
    for member in members:
        if not is_studier(member):
            continue
        if member.nick is None or list(map(lambda x: x.nick, members)).count(member.nick) > 1:
            user_name = member.name
        else:
            user_name = member.nick
        tup = cur.execute("SELECT total_time, required_hours FROM prevstudiers WHERE user_id = (?)", (member.id,)).fetchone()
        if not tup or tup[0] ==0:
            none.append(member)
        elif tup[0] < tup[1]:
            partial.append([member, tup[0], tup[1]])
        else:
            complete.append([member, tup[0], tup[1]])
    
    embeds=list()
    
    embeds.append(discord.Embed(title="**Members who completed all of their hours**", color=discord.Colour.blurple()))
    fields=1
    for tup in complete:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split('.')[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split('.')[0]
        if fields%25 != 0:
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
        fields+=1
    
    embeds.append(discord.Embed(title="**Members who completed only some of their hours**", color=discord.Colour.blurple()))
    fields=1
    for tup in partial:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split('.')[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split('.')[0]
        if fields%25 != 0:
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"{readable_actual} out of {readable_required}", inline=False)
        fields+=1
    
    embeds.append(discord.Embed(title="**Members who completed none of their hours**", color=discord.Colour.blurple()))
    fields=1
    for member in none:
        if member.nick is None:
            user_name = member.name
        else:
            user_name = member.nick
        if fields%25 != 0:
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"", inline=False)
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds)-1].add_field(name=f"{user_name}", value=f"", inline=False)
        fields+=1
    
    for embed in embeds:
        await ctx.respond(embed=embed)


#set required hours for user
@bot.slash_command(description = "Set required hours for a user")
async def setrequired(ctx, user: discord.Option(discord.Member, required="True", description="Which role do you want to give admin permissions to"), hours: discord.Option(int, required="True", description="How many hours per week")):
    user_id = user.id
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    cur.execute("UPDATE studiers SET required_hours = (?) WHERE user_id = (?)", (hours*3600, user_id))
    con.commit()
    await ctx.respond(f"{user_name} now needs {hours} hours per week!")


#force stop a session
@bot.slash_command(description = "End a user's session")
async def forcestop(ctx, user:discord.Option(discord.Member, required="True", description="Which user's session to end")):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    user_id = user.id
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    values = cur.execute(f"SELECT start_time, session_id FROM sessions WHERE user_id = (?) AND is_complete = 0", (user_id,)).fetchone()
    if not values:
        await ctx.respond(f"{user_name} has not started studying yet!")
        return
    start_time, sid = values
    duration = (discord.Object(ctx.interaction.id).created_at - datetime.timedelta(hours=5)).timestamp() - start_time
    cur.execute(f"UPDATE sessions SET duration = (?), activity = \"FORCESTOP\", is_complete = 1 WHERE session_id = (?)", (duration, sid))
    total_time = cur.execute(f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)).fetchone()[0]
    total_time += duration
    cur.execute(f"UPDATE studiers SET total_time = (?) WHERE user_id = (?)", (total_time, user_id))
    con.commit()
    #display time studied in readable format
    human_readable_duration = str(datetime.timedelta(seconds=duration)).split('.')[0]
    human_readable_total = str(datetime.timedelta(seconds=total_time)).split('.')[0]
    await ctx.respond(f"{user_name} spent {human_readable_duration} studying!\nTheir total time for the week is now {human_readable_total}")
    



########################## Tasks ##############################

#check if a user is in voice chat (and sharing screen) and @ them if they are not TODO TEST
@tasks.loop(minutes=15)
async def check_vc(ctx):
    user_id = int(ctx.author.id)
    check_session = cur.execute("SELECT session_id FROM sessions WHERE user_id = (?) AND is_complete = 0", (user_id,)).fetchone()
    if not check_session:
        check_vc.stop()
        return
    voice_state = ctx.author.voice
    if voice_state is None:
        await ctx.send(f"<@{user_id}> make sure you're in the **Study hours** channel!")





################# Extra functions and helpers #################

#return bool for if user has admin permissions (takes member)
def is_admin(member):
    for role in member.roles:
        if role.id in admin_roles:
            return True
    return False

#return bool for if user is a studier (takes member)
def is_studier(member):
    for role in member.roles:
        if role.id in studier_roles:
            return True
    return False

#return bool for if a user is under academic review (takes member)
def is_review(member):
    for role in member.roles:
        if role.id in review_roles:
            return True
    return False

#load admin list from database
def load_admin():
    admin_tups = cur.execute(f"SELECT role_id FROM roles WHERE purpose = \"Admin\"").fetchall()
    for tup in admin_tups:
        admin_roles.add(tup[0])

#load studier list from database
def load_studiers():
    studier_tups = cur.execute(f"SELECT role_id FROM roles WHERE purpose = \"Studier\"").fetchall()
    for tup in studier_tups:
        studier_roles.add(tup[0])

#load academic review list from database
def load_review():
    review_tups = cur.execute(f"SELECT role_id FROM roles WHERE purpose = \"Academic Review\"").fetchall()
    for tup in review_tups:
        review_roles.add(tup[0])


#list of commands and functionality for studiers
@bot.slash_command(description = "Show user manual for how to use the bot!")
async def help(ctx):
    embed = discord.Embed(title="**User Manual**", color=discord.Colour.blurple())
    embed.add_field(name="**/start**", value="Use to start a session. Can not be used if you already have an active session! Make sure that if you are under academic review you are joining the **Study hours** voice channel and sharing your screen during your session.", inline=False)
    embed.add_field(name="**/stop**", value="Use to end your session. Say what you did in the activity field (doesn't need to be complicated, just a simple statement)", inline=False)
    embed.add_field(name="**/subtract**", value="Subtract time if you accidentally forgot to end your session. Put the amount of hours in the hours field and minutes in the minutes field. Remember you still need to end the overdue session!", inline=False)
    embed.add_field(name="**/time**", value="Check your time. Put yourself in the user field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/getreport**", value="Get a detailed report of your activity for the week. Put yourself in the user field (discord should autocomplete)", inline=False)
    await ctx.respond(embed=embed)

#list of commands and functionality for admins
@bot.slash_command(description = "Show admin manual for all features of the bot!")
async def admin_help(ctx):
    embed = discord.Embed(title="**Admin Manual**", color=discord.Colour.blurple())
    embed.add_field(name="**/subtract**", value="Subtract time for a user. You can't subtract more hours than they have for the week. Put the name of the user in the user field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/add**", value="Add time for a user. Put the name of the user in the user field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/forcestop**", value="End an active session for a user. Only works if the user has an active session (**/activesessions**). Put the name of the user in the user field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/activesessions**", value="See which users have current active sessions and when they started.", inline=False)
    embed.add_field(name="**/prev_activesessions**", value="See which sessions are still active from last week. (for special cases)", inline=False)
    embed.add_field(name="**/getreport**", value="Get a report of all of a user's sessions for the week. Put the name of the user in the user field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/prev_getreport**", value="Get a report of all of a user's sessions for the previous week. Put the name of the user in the user field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/time**", value="Show how much time a user has for the week out of their required hours. Put the name of the user in the user field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/prev_time**", value="Show how much time a user has for the previous week out of their required hours. Put the name of the user in the user field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/serverreport**", value="Get a report of everyone in the server with a \"studier\" role (**/makestudier**) organized by whether they have all, some, or none of their hours.", inline=False)
    embed.add_field(name="**/prev_serverreport**", value="Get last week's report of everyone in the server with a \"studier\" role (**/makestudier**) organized by whether they have all, some, or none of their hours.", inline=False)
    embed.add_field(name="**/setrequired**", value="Set required hours for a user. Put the name of the user in the user field (discord should autocomplete) and the amount of required hours in the hours field.", inline=False)
    embed.add_field(name="**/clear**", value="Clear data for the week. Data for the previous week will be wiped and the current week's data will replace it. Confirm by entering \"Yes I am sure\" exactly in the confirmation field.", inline=False)
    embed.add_field(name="**/makestudier**", value="Assign a role to be for studiers. This allows them to show up in the **/serverreport** function. Enter the role in the role field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/removestudier**", value="Unassign a role to be for studiers. This disallows them to show up in the **/serverreport** function. Enter the role in the role field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/promote**", value="Assign a user to be an admin. This allows them to use this set of functions. Enter the role in the role field (discord should autocomplete)", inline=False)
    embed.add_field(name="**/demote**", value="Unassign a user to be an admin. This disallows them to use this set of functions. Enter the role in the role field (discord should autocomplete)", inline=False)
    await ctx.respond(embed=embed)
    


###start bot
bot.run(BOT_TOKEN)




#TODO list
    #something is wrong with start stop functionality and responses are erroring for some reason idk figure that out
    
    #make a single function for promotion / demotion and studier roles and academic review roles (or two) (and single load function)
    #daily routine - ping people who are behind, clear at end of week, call report weekly
    #hourly(?) routine(task) - check for active sessions vs people in voice chat, ping admins?, function to ignore for somebody?
    #make role for academic review people and something to check if they are in call - lowkey just read the one above nvm
    #the entire competition tracker - use JSON?
        #add activity
        #modify activity (points, description?)
        #view leaderboard - individual and team
        #task to display leaderboard?
        #view point breakdown for individual person
        #view point breakdown for team
    #help function - user and admin - made but make sure it stays accurate
    #(not bot) rename study captain to academic coordinator (for their resumes)
    #(not bot) dont start AMs on academic review but scholarship chair or study captain can make them at any time? actives on academic review if under 2.7 term or midterm (unless midterms are stupid)
    #make code cleaner - functions for permission check, existence check, finding username, etc. - do not need f strings for queries (usually) - modularize!!!?
    #track classes?
