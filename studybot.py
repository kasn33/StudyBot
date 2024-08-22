# version 1.8.22.24
# contact Kyle Seifert AΨ722 somehow if this isn't me and you have questions or something
# IF YOU HELP WITH THIS BOT YOU CAN TALK ABOUT IT IN INTERVIEWS - converting the whole thing to typescript would be a very good project since python is losing discord support and typescript is useful (NODEJS!!!!)
# need to pip install py-cord and also python obviously
# there are functions to set and load things like roles, but for specific stuff like default required hours and channel IDs change the value in the code here at the top
# ^ same goes for things like help menu mentioning specific "Study hours" channel (the code doesn't actually track that channel vs others, name only relevant for help)

import discord
from discord import option
from discord.ext import commands, tasks
import asyncio
import datetime
import sqlite3
import os
import json


BOT_TOKEN = ""
CHANNEL_ID = 1227722112404553889
SERVER_ID = 1227721401239343187
intents = discord.Intents.all()
client = discord.Client(intents=intents)
DEFAULT_REQUIRED = 32400  # in seconds (9 hours)
LONG_TIME = 32400  # time to check if studier is still there (in seconds (9 hours))
admin_roles, studier_roles, review_roles = set(), set(), set()
cst = utc = datetime.timezone(datetime.timedelta(hours=3))
DAILY_CHECK_TIME = datetime.time(hour=7, tzinfo=cst)


bot = commands.Bot(
    command_prefix="!", intents=intents
)  # prefix is old but maybe useful

# initialize / connect database
con = sqlite3.connect("hours.db")
cur = con.cursor()


# startup message (console and channel in server)
@bot.event
async def on_ready():
    cur.execute(
        f"""CREATE TABLE IF NOT EXISTS studiers(
        user_id INTEGER PRIMARY KEY,
        total_time INTEGER DEFAULT 0,
        required_hours INTEGER DEFAULT {DEFAULT_REQUIRED}
    );"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS sessions(
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        start_time INTEGER,
        is_complete INTEGER DEFAULT 0,
        duration INTEGER,
        activity TEXT,
        FOREIGN KEY (user_id) REFERENCES studiers(user_id)
    );"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS roles(
        purp_id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_id INTEGER,
        purpose TEXT
    );"""
    )
    con.commit()
    load_admin()
    load_studiers()
    load_review()
    print("Study bot is ready!")
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Hello! Study bot is ready!")


################# Extra functions and helpers #################


# get a user's nickname
def getName(member):
    if member.display_name is None:
        return member.name
    else:
        return member.display_name


# return bool for if user has admin permissions (takes member)
def is_admin(member):
    for role in member.roles:
        if role.id in admin_roles:
            return True
    return False


# return bool for if user is a studier (takes member)
def is_studier(member):
    for role in member.roles:
        if role.id in studier_roles:
            return True
    return False


# return bool for if a user is under academic review (takes member)
def is_review(member):
    for role in member.roles:
        if role.id in review_roles:
            return True
    return False


# load admin list from database
def load_admin():
    admin_tups = cur.execute(
        f'SELECT role_id FROM roles WHERE purpose = "Admin"'
    ).fetchall()
    for tup in admin_tups:
        admin_roles.add(tup[0])


# load studier list from database
def load_studiers():
    studier_tups = cur.execute(
        f'SELECT role_id FROM roles WHERE purpose = "Studier"'
    ).fetchall()
    for tup in studier_tups:
        studier_roles.add(tup[0])


# load academic review list from database
def load_review():
    review_tups = cur.execute(
        f'SELECT role_id FROM roles WHERE purpose = "Academic Review"'
    ).fetchall()
    for tup in review_tups:
        review_roles.add(tup[0])


# load activities from JSON file
def loadActivities():
    with open("activities.json", "r") as file:
        return json.load(file)


# dump activities into JSON file
def dumpActivities(data):
    with open("activities.json", "w") as file:
        json.dump(data, file)


# check if activities is empty
def isActivitiesEmpty():
    try:
        return not os.path.getsize("activities.json")
    except:
        return True


# load competition data from JSON file
def loadCompetitors():
    with open("competitors.json", "r") as file:
        return json.load(file)


# dump competition data into JSON file
def dumpCompetitors(data):
    with open("competitors.json", "w") as file:
        json.dump(data, file)


# check if competition data is empty
def isCompetitorsEmpty():
    try:
        return not os.path.getsize("competitors.json")
    except:
        return True


def getActivityAutocomplete(ctx: discord.AutocompleteContext):
    if isActivitiesEmpty():
        return []
    activities = loadActivities()
    return list(activities.keys())


def getUserActivityAutocomplete(ctx: discord.AutocompleteContext):
    if isCompetitorsEmpty():
        return []
    competitors = loadCompetitors()
    if str(ctx.options["user"]) not in competitors:
        return []
    competitor = competitors[str(ctx.options["user"])]
    return list(competitor["activities"].keys())


def getGroupNames():
    if isCompetitorsEmpty():
        return []
    groupNames = list()
    competitors = loadCompetitors()
    for competitor in competitors.values():
        if competitor["group"] not in groupNames:
            groupNames.append(competitor["group"])
    return groupNames


def getGroupAutocomplete(ctx: discord.AutocompleteContext):
    return getGroupNames()


# list of commands and functionality for studiers
@bot.slash_command(description="Show user manual for how to use the bot!")
async def help(ctx):
    embed = discord.Embed(title="**User Manual**", color=discord.Colour.blurple())
    embed.add_field(
        name="**/start**",
        value="Use to start a session. Can not be used if you already have an active session! Make sure that if you are under academic review you are joining the **Study hours** voice channel and sharing your screen during your session.",
        inline=False,
    )
    embed.add_field(
        name="**/stop**",
        value="Use to end your session. Say what you did in the activity field (doesn't need to be complicated, just a simple statement)",
        inline=False,
    )
    embed.add_field(
        name="**/subtract**",
        value="Subtract time if you accidentally forgot to end your session. Put the amount of hours in the hours field and minutes in the minutes field. Remember you still need to end an overdue session!",
        inline=False,
    )
    embed.add_field(
        name="**/time**",
        value="Check your time. Put yourself in the user field (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/getreport**",
        value="Get a detailed report of your activity for the week. Put yourself in the user field (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/seeactivities**",
        value="Get a list of valid activities for the competition",
        inline=False,
    )
    embed.add_field(
        name="**/stats**",
        value="See a user's stats for the competition (user should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/groupstats**",
        value="See a group's stats for the competition (group should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/listgroups**",
        value="See a list of groups and their members for the competition",
        inline=False,
    )
    embed.add_field(
        name="**/leaderboard**",
        value="See the leaderboard for top groups in the competition",
        inline=False,
    )
    embed.add_field(
        name="**/sololeaderboard**",
        value="See the solo leaderboard for the top 10 competitors in the competition",
        inline=False,
    )
    await ctx.respond(embed=embed)


# list of commands and functionality for admins
@bot.slash_command(
    description="Show admin manual for all privileged features of the bot!"
)
async def admin_help(ctx):
    embed = discord.Embed(title="**Admin Manual**", color=discord.Colour.blurple())
    embed2 = discord.Embed(title="", color=discord.Colour.blurple())
    embed.add_field(
        name="**/subtract**",
        value="Subtract time for a user. You can't subtract more hours than they have for the week. Put the name of the user in the user field (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/add**",
        value="Add time for a user. Put the name of the user in the user field (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/forcestop**",
        value="End an active session for a user. Only works if the user has an active session (**/activesessions**). Put the name of the user in the user field (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/activesessions**",
        value="See which users have current active sessions and when they started.",
        inline=False,
    )
    embed.add_field(
        name="**/prev_activesessions**",
        value="See which sessions are still active from last week. (for special cases)",
        inline=False,
    )
    embed.add_field(
        name="**/getreport**",
        value="Get a report of all of a user's sessions for the week. Put the name of the user in the user field (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/prev_getreport**",
        value="Get a report of all of a user's sessions for the previous week. Put the name of the user in the user field (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/time**",
        value="Show how much time a user has for the week out of their required hours. Put the name of the user in the user field (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/prev_time**",
        value="Show how much time a user has for the previous week out of their required hours. Put the name of the user in the user field (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/serverreport**",
        value='Get a report of everyone in the server with a "studier" role (**/makestudier**) organized by whether they have all, some, or none of their hours.',
        inline=False,
    )
    embed.add_field(
        name="**/prev_serverreport**",
        value='Get last week\'s report of everyone in the server with a "studier" role (**/makestudier**) organized by whether they have all, some, or none of their hours.',
        inline=False,
    )
    embed.add_field(
        name="**/groupreport**",
        value='Get study hour report for group members with required study hours',
        inline=False,
    )
    embed.add_field(
        name="**/prev_groupreport**",
        value="Get previous week's study hour report for group members with required study hours",
        inline=False,
    )
    embed.add_field(
        name="**/setrequired**",
        value="Set required hours for a user. Put the name of the user in the user field (discord should autocomplete) and the amount of required hours in the hours field.",
        inline=False,
    )
    embed.add_field(
        name="**/clear**",
        value='Clear data for the week. Data for the previous week will be wiped and the current week\'s data will replace it. Confirm by entering "Yes I am sure" exactly in the confirmation field.',
        inline=False,
    )
    embed.add_field(
        name="**/promote**",
        value="Assign a type to a role. Select the type from the drop down for perm. Select the role to apply that type to for role (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/demote**",
        value="Remove a type from a role. Select the type from the drop down for perm. Select the role to remove that type from (if it already has it) for role (discord should autocomplete)",
        inline=False,
    )
    embed.add_field(
        name="**/addactivity**",
        value="Add an activity to the catalog. Enter the name, description, point value, and whether it can be completed more than once by one person.",
        inline=False,
    )
    embed.add_field(
        name="**/modifyactivity**",
        value="Modify attributes of an activity. This might break things but hopefully not.",
        inline=False,
    )
    embed.add_field(
        name="**/removeactivity**",
        value="Remove an activity from the catalog. There's a good shot this breaks things if anyone's done it already.",
        inline=False,
    )
    embed.add_field(
        name="**/makegroup**",
        value="Make a group for the competition with the leader. Only one leader per group.",
        inline=False,
    )
    embed.add_field(
        name="**/addmember**",
        value="Add a member to a group. The group should autocomplete.",
        inline=False,
    )
    embed.add_field(
        name="**/completeactivity**",
        value="Complete an activity for a user. Both user and activity should autocomplete.",
        inline=False,
    )
    embed.add_field(
        name="**/uncompleteactivity**",
        value="Uncomplete an activity for a user. Both user and activity should autocomplete. Specify value if something's wrong with the data.",
        inline=False,
    )
    embed.add_field(
        name="**/addpoints**",
        value="Add points to a user without an associated activity. Specify the point value and reason.",
        inline=False,
    )
    embed2.add_field(
        name="**/subtractpoints**",
        value="Subtract points from a user without an associated activity. Specify the point value and reason.",
        inline=False,
    )

    await ctx.respond(embed=embed)
    await ctx.respond(embed=embed2)


###################################### Study tracker functions ######################################


# start studying session
@bot.slash_command(description="Start your study session")
async def start(ctx):
    user_id = int(ctx.author.id)
    check_studier = cur.execute(
        f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)
    ).fetchone()
    if not check_studier:
        cur.execute(f"INSERT INTO studiers (user_id) VALUES (?)", (user_id,))
    check_session = cur.execute(
        f"SELECT start_time FROM sessions WHERE user_id = (?) AND is_complete = 0",
        (user_id,),
    ).fetchone()
    if check_session:
        await ctx.respond(f"<@{user_id}> Session already active!")
        return
    start_time = discord.Object(ctx.interaction.id).created_at - datetime.timedelta(
        hours=5
    )
    start_timestamp = start_time.timestamp()
    cur.execute(
        f"INSERT INTO sessions (user_id, start_time) VALUES (?,?)",
        (user_id, start_timestamp),
    )
    con.commit()

    # check if user is on academic review and start checker routine if they are
    if not check_long.next_iteration:
        check_long.start(ctx)
    if is_review(ctx.author) and not check_vc.next_iteration:
        check_vc.start(ctx)

    # display time in readable format
    human_readable_time = start_time.strftime("%H:%M:%S")
    await ctx.respond(
        f"<@{user_id}> New study session started at {human_readable_time}"
    )


# stop studying session
@bot.slash_command(description="End your study session and say what you did")
async def stop(
    ctx,
    activity: discord.Option(
        str,
        required=True,
        description="What did you do? This can be a simple statement.",
    ),
):
    user_id = int(ctx.author.id)
    values = cur.execute(
        f"SELECT start_time, session_id FROM sessions WHERE user_id = (?) AND is_complete = 0",
        (user_id,),
    ).fetchone()
    if not values:
        await ctx.respond(f"<@{user_id}> You haven't started studying yet!")
        return
    start_time, sid = values
    duration = (
        discord.Object(ctx.interaction.id).created_at - datetime.timedelta(hours=5)
    ).timestamp() - start_time
    cur.execute(
        f"UPDATE sessions SET duration = (?), activity = (?), is_complete = 1 WHERE session_id = (?)",
        (duration, activity, sid),
    )
    total_time = cur.execute(
        f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)
    ).fetchone()[0]
    total_time += duration
    cur.execute(
        f"UPDATE studiers SET total_time = (?) WHERE user_id = (?)",
        (total_time, user_id),
    )
    con.commit()

    # display time studied in readable format
    human_readable_duration = str(datetime.timedelta(seconds=duration)).split(".")[0]
    human_readable_total = str(datetime.timedelta(seconds=total_time)).split(".")[0]
    await ctx.respond(
        f"<@{user_id}> You spent {human_readable_duration} studying!\nYour total time for the week is now {human_readable_total}"
    )


# check how much time a user has spent studying this week
@bot.slash_command(description="Check the time for a user")
async def time(
    ctx,
    user: discord.Option(
        discord.Member,
        required=True,
        description="Who you want to check the hours of (could be you)",
    ),
):
    user_id = user.id
    if not is_admin(ctx.author) and user_id != int(ctx.author.id):
        await ctx.respond("You don't have permission to check other people!")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    tup = cur.execute(
        f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)
    ).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studying this week.")
        return
    time_spent = tup[0]
    human_readable_time = str(datetime.timedelta(seconds=time_spent)).split(".")[0]
    await ctx.respond(f"{user_name} has {human_readable_time} study hours this week!")


# check how much time a user has spent studying the previous week
@bot.slash_command(description="Check the time for a user last week")
async def prev_time(
    ctx,
    user: discord.Option(
        discord.Member,
        required=True,
        description="Who you want to check the hours of (could be you)",
    ),
):
    user_id = user.id
    if not is_admin(ctx.author) and user_id != int(ctx.author.id):
        await ctx.respond("You don't have permission to check other people!")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    tup = cur.execute(
        f"SELECT total_time FROM prevstudiers WHERE user_id = (?)", (user_id,)
    ).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} did not start studying last week.")
        return
    time_spent = tup[0]
    human_readable_time = str(datetime.timedelta(seconds=time_spent)).split(".")[0]
    await ctx.respond(f"{user_name} has {human_readable_time} study hours this week!")


# show all sessions for a user (need permission if not that user) (won't work if over 25 sessions but there aint no way)
@bot.slash_command(description="Show all of a user's activity for the week")
async def getreport(
    ctx,
    user: discord.Option(
        discord.Member,
        required=True,
        description="Who you want to check the activity of (could be you)",
    ),
):
    user_id = user.id
    if not is_admin(ctx.author) and user_id != int(ctx.author.id):
        await ctx.respond("You don't have permission to check other people!")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick

    embeds = list()
    embeds.append(
        discord.Embed(
            title=f"**Report for {user_name}**", color=discord.Colour.blurple()
        )
    )
    fields = 1
    tup = cur.execute(
        "SELECT total_time, required_hours FROM studiers WHERE user_id = (?)",
        (user_id,),
    ).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studing this week")
        return
    total_time, required_hours = tup
    embeds[0].add_field(
        name="**Total Activity**",
        value=f"{user_name} has completed **{str(datetime.timedelta(seconds=total_time)).split('.')[0]}** out of **{str(datetime.timedelta(seconds=required_hours)).split('.')[0]}**",
    )
    sessions = cur.execute(
        f"SELECT start_time, duration, activity FROM sessions WHERE user_id = (?) AND is_complete = 1 ORDER BY start_time",
        (user_id,),
    ).fetchall()
    for tup in sessions:
        readable_time = (
            datetime.datetime.fromtimestamp(tup[0]) + datetime.timedelta(hours=5)
        ).strftime("**%A** starting at %H:%M")
        if fields % 25 != 0:
            embeds[len(embeds) - 1].add_field(
                name=f"{readable_time}",
                value=f"Spent **{str(datetime.timedelta(seconds=tup[1])).split('.')[0]}** doing: {tup[2]}",
                inline=False,
            )
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds) - 1].add_field(
                name=f"{readable_time}",
                value=f"Spent **{str(datetime.timedelta(seconds=tup[1])).split('.')[0]}** doing: {tup[2]}",
                inline=False,
            )
        fields += 1
    for embed in embeds:
        await ctx.respond(embed=embed)


# show all sessions for a user for the previous week (need permission if not that user)
@bot.slash_command(description="Show all of a user's activity for the previous week")
async def prev_getreport(
    ctx,
    user: discord.Option(
        discord.Member,
        required=True,
        description="Who you want to check the activity of (could be you)",
    ),
):
    user_id = user.id
    if not is_admin(ctx.author) and user_id != int(ctx.author.id):
        await ctx.respond("You don't have permission to check other people!")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick

    embeds = list()
    embeds.append(
        discord.Embed(
            title=f"**Report for {user_name}**", color=discord.Colour.blurple()
        )
    )
    fields = 1
    tup = cur.execute(
        "SELECT total_time, required_hours FROM prevstudiers WHERE user_id = (?)",
        (user_id,),
    ).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studing this week")
        return
    total_time, required_hours = tup
    embeds[0].add_field(
        name="**Previous Week Total Activity**",
        value=f"{user_name} has completed **{str(datetime.timedelta(seconds=total_time)).split('.')[0]}** out of **{str(datetime.timedelta(seconds=required_hours)).split('.')[0]}**",
    )
    sessions = cur.execute(
        f"SELECT start_time, duration, activity FROM prevsessions WHERE user_id = (?) AND is_complete = 1 ORDER BY start_time",
        (user_id,),
    ).fetchall()
    for tup in sessions:
        readable_time = (
            datetime.datetime.fromtimestamp(tup[0]) + datetime.timedelta(hours=5)
        ).strftime("**%A** starting at %H:%M")
        if fields % 25 != 0:
            embeds[len(embeds) - 1].add_field(
                name=f"{readable_time}",
                value=f"Spent **{str(datetime.timedelta(seconds=tup[1])).split('.')[0]}** doing: {tup[2]}",
                inline=False,
            )
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds) - 1].add_field(
                name=f"{readable_time}",
                value=f"Spent **{str(datetime.timedelta(seconds=tup[1])).split('.')[0]}** doing: {tup[2]}",
                inline=False,
            )
        fields += 1
    for embed in embeds:
        await ctx.respond(embed=embed)


# remove time from a user (needs permission) (less than 24 hours)
@bot.slash_command(description="Add time to somebody (less than 24 hours)")
async def addtime(
    ctx,
    user: discord.Option(
        discord.Member,
        required=True,
        description="Who you want to add time to (could be you)",
    ),
    hours: discord.Option(int),
    minutes: discord.Option(int),
    reason: discord.Option(str),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    user_id = user.id
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    tup = cur.execute(
        f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)
    ).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studying this week.")
        return
    orig_time = tup[0]
    duration = datetime.timedelta(hours=hours, minutes=minutes).seconds
    new_time = orig_time + duration
    cur.execute(
        f"UPDATE studiers SET total_time = (?) WHERE user_id = (?)", (new_time, user_id)
    )
    current_time = discord.Object(ctx.interaction.id).created_at.timestamp()
    cur.execute(
        f"INSERT INTO sessions (start_time, is_complete, user_id, duration, activity) VALUES (?,?,?,?,?)",
        (current_time, 1, user_id, duration, f"Added by admin: {reason}"),
    )
    con.commit()

    human_readable_orig = str(datetime.timedelta(seconds=orig_time)).split(".")[0]
    human_readable_new = str(datetime.timedelta(seconds=new_time)).split(".")[0]
    await ctx.respond(
        f"Changed hours for {user_name} from {human_readable_orig} to {human_readable_new}"
    )


# add time to a user (needs permission) (less than 24 hours)
@bot.slash_command(description="Remove time from somebody (less than 24 hours)")
async def subtracttime(
    ctx,
    user: discord.Option(
        discord.Member,
        required=True,
        description="Who you want to remove time from (could be you)",
    ),
    hours: discord.Option(int),
    minutes: discord.Option(int),
    reason: discord.Option(str),
):
    if hours < 0 or minutes < 0:
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
    tup = cur.execute(
        f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)
    ).fetchone()
    if not tup:
        await ctx.respond(f"{user_name} has not started studying this week.")
        return
    orig_time = tup[0]
    duration = datetime.timedelta(hours=hours, minutes=minutes).seconds
    new_time = orig_time - duration
    if new_time < 0:
        await ctx.respond("Cannot set total time negative!")
        return
    cur.execute(
        f"UPDATE studiers SET total_time = (?) WHERE user_id = (?)", (new_time, user_id)
    )
    current_time = discord.Object(ctx.interaction.id).created_at.timestamp()
    cur.execute(
        f"INSERT INTO sessions (start_time, is_complete, user_id, duration, activity) VALUES (?,?,?,?,?)",
        (current_time, 1, user_id, duration * (-1), f"Subtracted by admin: {reason}"),
    )
    con.commit()

    human_readable_orig = str(datetime.timedelta(seconds=orig_time)).split(".")[0]
    human_readable_new = str(datetime.timedelta(seconds=new_time)).split(".")[0]
    await ctx.respond(
        f"Changed hours for {user_name} from {human_readable_orig} to {human_readable_new}"
    )


# add role for admin (must be server administrator)
@bot.slash_command(
    description="Add a type of permissions to a role (must be server admin)"
)
async def promote(
    ctx,
    perm: discord.Option(
        str,
        choices=["Studier", "Admin", "Academic Review"],
        required=True,
        description="What type of 'permission' do you want to give this role?",
    ),
    role: discord.Option(
        discord.Role,
        required=True,
        description="Which role do you want to give admin permissions to",
    ),
):
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


# remove role for admin (must be server administrator)
@bot.slash_command(
    description="Remove a type of permissions from a role (must be server admin)"
)
async def demote(
    ctx,
    perm: discord.Option(
        str,
        choices=["Studier", "Admin", "Academic Review"],
        required=True,
        description="What type of 'permission' do you want to remove from this role?",
    ),
    role: discord.Option(
        discord.Role,
        required=True,
        description="Which role do you want to take admin permissions from",
    ),
):
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
    cur.execute(
        "DELETE FROM roles WHERE role_id = (?) AND purpose = (?)", (role.id, perm)
    )
    con.commit()


# clear all the data to start a fresh week
@bot.slash_command(description="Clear all data for the week (BE CAREFUL)")
async def clear(
    ctx,
    confirmation: discord.Option(
        str, description='Type "Yes I am sure" if you\'re sure'
    ),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if confirmation != "Yes I am sure":
        await ctx.respond("Make sure you're sure")
        return
    cur.execute("DROP TABLE IF EXISTS prevstudiers")
    cur.execute("DROP TABLE IF EXISTS prevsessions")
    cur.execute("CREATE TABLE IF NOT EXISTS prevstudiers AS SELECT * FROM studiers")
    cur.execute("CREATE TABLE IF NOT EXISTS prevsessions AS SELECT * FROM sessions")
    cur.execute("UPDATE studiers SET total_time = 0")
    cur.execute("DELETE FROM sessions")
    con.commit()
    await ctx.respond("Weekly data reset!")


# list current active sessions (embeds have a limit so does not scale past 25 - should never be an issue)
@bot.slash_command(description="Show all live sessions")
async def activesessions(ctx):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    sessions = cur.execute(
        "SELECT user_id, start_time FROM sessions WHERE is_complete = 0"
    ).fetchall()
    embed = discord.Embed(title="Active Sessions", color=discord.Colour.blurple())
    for session in sessions:
        user = bot.get_user(session[0])
        if user.display_name is None:
            user_name = user.name
        else:
            user_name = user.display_name
        human_readable_time = (datetime.datetime.fromtimestamp(session[1])).strftime(
            "%A, %H:%M:%S"
        )
        embed.add_field(
            name=f"**{user_name}**", value=f"Active since {human_readable_time}"
        )
    await ctx.respond(embed=embed)


# list overdue sessions from past week (allow admin to add based on it or whatever is needed) (embeds have a limit so does not scale past 25 - should never be an issue)
@bot.slash_command(description="Show suspended sessions from previous week")
async def prev_activesessions(ctx):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    sessions = cur.execute(
        "SELECT user_id, start_time FROM prevsessions WHERE is_complete = 0"
    ).fetchall()
    embed = discord.Embed(title="Active Sessions", color=discord.Colour.blurple())
    for session in sessions:
        user = bot.get_user(session[0])
        if user.display_name is None:
            user_name = user.name
        else:
            user_name = user.display_name
        human_readable_time = (datetime.datetime.fromtimestamp(session[1])).strftime(
            "%A, %H:%M:%S"
        )
        embed.add_field(
            name=f"**{user_name}**", value=f"Active since {human_readable_time}"
        )
    await ctx.respond(embed=embed)


# list all users by if they've completed their hours (and how many of their required hours are done)
@bot.slash_command(description="Show time for all server members with required hours")
async def serverreport(ctx):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    complete, partial, none, never = list(), list(), list(), list()
    guild = ctx.guild
    members = await guild.fetch_members(limit=None).flatten()
    nicknames = (
        set()
    )  # used to verify uniqueness of names (so there can't be 10 people named Steve)
    for member in members:
        if member.nick is not None and is_studier(member):
            nicknames.add(member.nick)
    for member in members:
        if not is_studier(member):
            continue
        if (
            member.nick is None
            or list(map(lambda x: x.nick, members)).count(member.nick) > 1
        ):
            user_name = member.name
        else:
            user_name = member.nick
        tup = cur.execute(
            "SELECT total_time, required_hours FROM studiers WHERE user_id = (?)",
            (member.id,),
        ).fetchone()
        if not tup or tup[0] == 0:
            none.append(member)
        elif tup[0] < tup[1]:
            partial.append([member, tup[0], tup[1]])
        else:
            complete.append([member, tup[0], tup[1]])

    embeds = list()

    embeds.append(
        discord.Embed(
            title="**Members who completed all of their hours**",
            color=discord.Colour.blurple(),
        )
    )
    fields = 1
    for tup in complete:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split(".")[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split(".")[0]
        if fields % 25 != 0:
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}",
                value=f"{readable_actual} out of {readable_required}",
                inline=False,
            )
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}",
                value=f"{readable_actual} out of {readable_required}",
                inline=False,
            )
        fields += 1

    embeds.append(
        discord.Embed(
            title="**Members who completed only some of their hours**",
            color=discord.Colour.blurple(),
        )
    )
    fields = 1
    for tup in partial:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split(".")[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split(".")[0]
        if fields % 25 != 0:
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}",
                value=f"{readable_actual} out of {readable_required}",
                inline=False,
            )
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}",
                value=f"{readable_actual} out of {readable_required}",
                inline=False,
            )
        fields += 1

    embeds.append(
        discord.Embed(
            title="**Members who completed none of their hours**",
            color=discord.Colour.blurple(),
        )
    )
    fields = 1
    for member in none:
        if member.nick is None:
            user_name = member.name
        else:
            user_name = member.nick
        if fields % 25 != 0:
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}", value=f"", inline=False
            )
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}", value=f"", inline=False
            )
        fields += 1

    for embed in embeds:
        await ctx.respond(embed=embed)


# list all users by if they've completed their hours last week (and how many of their required hours are done)
@bot.slash_command(
    description="Show previous week time for all server members with required hours"
)
async def prev_serverreport(ctx):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    complete, partial, none, never = list(), list(), list(), list()
    guild = ctx.guild
    members = await guild.fetch_members(limit=None).flatten()
    nicknames = (
        set()
    )  # used to verify uniqueness of names (so there can't be 10 people named Steve)
    for member in members:
        if member.nick is not None and is_studier(member):
            nicknames.add(member.nick)
    for member in members:
        if not is_studier(member):
            continue
        if (
            member.nick is None
            or list(map(lambda x: x.nick, members)).count(member.nick) > 1
        ):
            user_name = member.name
        else:
            user_name = member.nick
        tup = cur.execute(
            "SELECT total_time, required_hours FROM prevstudiers WHERE user_id = (?)",
            (member.id,),
        ).fetchone()
        if not tup or tup[0] == 0:
            none.append(member)
        elif tup[0] < tup[1]:
            partial.append([member, tup[0], tup[1]])
        else:
            complete.append([member, tup[0], tup[1]])

    embeds = list()

    embeds.append(
        discord.Embed(
            title="**Members who completed all of their hours**",
            color=discord.Colour.blurple(),
        )
    )
    fields = 1
    for tup in complete:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split(".")[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split(".")[0]
        if fields % 25 != 0:
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}",
                value=f"{readable_actual} out of {readable_required}",
                inline=False,
            )
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}",
                value=f"{readable_actual} out of {readable_required}",
                inline=False,
            )
        fields += 1

    embeds.append(
        discord.Embed(
            title="**Members who completed only some of their hours**",
            color=discord.Colour.blurple(),
        )
    )
    fields = 1
    for tup in partial:
        if tup[0].nick is None:
            user_name = tup[0].name
        else:
            user_name = tup[0].nick
        readable_actual = str(datetime.timedelta(seconds=tup[1])).split(".")[0]
        readable_required = str(datetime.timedelta(seconds=tup[2])).split(".")[0]
        if fields % 25 != 0:
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}",
                value=f"{readable_actual} out of {readable_required}",
                inline=False,
            )
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}",
                value=f"{readable_actual} out of {readable_required}",
                inline=False,
            )
        fields += 1

    embeds.append(
        discord.Embed(
            title="**Members who completed none of their hours**",
            color=discord.Colour.blurple(),
        )
    )
    fields = 1
    for member in none:
        if member.nick is None:
            user_name = member.name
        else:
            user_name = member.nick
        if fields % 25 != 0:
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}", value=f"", inline=False
            )
        else:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
            embeds[len(embeds) - 1].add_field(
                name=f"{user_name}", value=f"", inline=False
            )
        fields += 1

    for embed in embeds:
        await ctx.respond(embed=embed)


@bot.slash_command(description="Show study hour report for group members who have required hours")
async def groupreport(ctx, group_name: discord.Option(
        str,
        required=True,
        description="Name of the group to get a report for",
        autocomplete=getGroupAutocomplete,
    )):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if isCompetitorsEmpty():
        await ctx.respond("There is no group by that name! (There are no competitors)")
        return
    competitors = loadCompetitors()
    if group_name not in getGroupNames():
        await ctx.respond(f"There is no group named '{group_name}'")
        return
    guild = ctx.guild
    members = await guild.fetch_members(limit=None).flatten()
    groupStudiers = []
    for member in members:
        if str(member.id) in competitors and competitors[str(member.id)]["group"] == group_name and is_studier(member):
            groupStudiers.append(member.id)
    if len(groupStudiers) == 0:
        await ctx.respond(f"Group '{group_name}' has no members with required study hours")
        return
    embed = discord.Embed(color=discord.Colour.blurple(), title=f"Study hour report for '{group_name}'")
    for studier in groupStudiers:
        tup = cur.execute(
            "SELECT total_time, required_hours FROM studiers WHERE user_id = (?)",
            (studier,),
        ).fetchone()
        if not tup:
            embed.add_field(name=f"{getName(bot.get_user(int(studier)))}", value="No record found", inline=False)
        else:
            readable_actual = str(datetime.timedelta(seconds=tup[0])).split(".")[0]
            readable_required = str(datetime.timedelta(seconds=tup[1])).split(".")[0]
            embed.add_field(name=f"{getName(bot.get_user(int(studier)))}", value=f"{readable_actual} out of {readable_required}", inline=False)
    await ctx.respond(embed=embed)
    
@bot.slash_command(description="Show previous week's study hour report for group members who have required hours")
async def prev_groupreport(ctx, group_name: discord.Option(
        str,
        required=True,
        description="Name of the group to get a report for",
        autocomplete=getGroupAutocomplete,
    )):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if isCompetitorsEmpty():
        await ctx.respond("There is no group by that name! (There are no competitors)")
        return
    competitors = loadCompetitors()
    if group_name not in getGroupNames():
        await ctx.respond(f"There is no group named '{group_name}'")
        return
    guild = ctx.guild
    members = await guild.fetch_members(limit=None).flatten()
    groupStudiers = []
    for member in members:
        if str(member.id) in competitors and competitors[str(member.id)]["group"] == group_name and is_studier(member):
            groupStudiers.append(member.id)
    if len(groupStudiers) == 0:
        await ctx.respond(f"Group '{group_name}' has no members with required study hours")
        return
    embed = discord.Embed(color=discord.Colour.blurple(), title=f"Previous week study hour report for '{group_name}'")
    for studier in groupStudiers:
        tup = cur.execute(
            "SELECT total_time, required_hours FROM prevstudiers WHERE user_id = (?)",
            (studier,),
        ).fetchone()
        if not tup:
            embed.add_field(name=f"{getName(bot.get_user(int(studier)))}", value="No record found", inline=False)
        else:
            readable_actual = str(datetime.timedelta(seconds=tup[0])).split(".")[0]
            readable_required = str(datetime.timedelta(seconds=tup[1])).split(".")[0]
            embed.add_field(name=f"{getName(bot.get_user(int(studier)))}", value=f"{readable_actual} out of {readable_required}", inline=False)
    await ctx.respond(embed=embed)
            


# set required hours for user
@bot.slash_command(description="Set required hours for a user")
async def setrequired(
    ctx,
    user: discord.Option(
        discord.Member,
        required=True,
        description="Which role do you want to give admin permissions to",
    ),
    hours: discord.Option(int, required=True, description="How many hours per week"),
):
    user_id = user.id
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    cur.execute(
        "UPDATE studiers SET required_hours = (?) WHERE user_id = (?)",
        (hours * 3600, user_id),
    )
    con.commit()
    await ctx.respond(f"{user_name} now needs {hours} hours per week!")


# force stop a session
@bot.slash_command(description="End a user's session")
async def forcestop(
    ctx,
    user: discord.Option(
        discord.Member, required=True, description="Which user's session to end"
    ),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    user_id = user.id
    if user.nick is None:
        user_name = user.name
    else:
        user_name = user.nick
    values = cur.execute(
        f"SELECT start_time, session_id FROM sessions WHERE user_id = (?) AND is_complete = 0",
        (user_id,),
    ).fetchone()
    if not values:
        await ctx.respond(f"{user_name} has not started studying yet!")
        return
    start_time, sid = values
    duration = (
        discord.Object(ctx.interaction.id).created_at - datetime.timedelta(hours=5)
    ).timestamp() - start_time
    cur.execute(
        f'UPDATE sessions SET duration = (?), activity = "FORCESTOP", is_complete = 1 WHERE session_id = (?)',
        (duration, sid),
    )
    total_time = cur.execute(
        f"SELECT total_time FROM studiers WHERE user_id = (?)", (user_id,)
    ).fetchone()[0]
    total_time += duration
    cur.execute(
        f"UPDATE studiers SET total_time = (?) WHERE user_id = (?)",
        (total_time, user_id),
    )
    con.commit()
    # display time studied in readable format
    human_readable_duration = str(datetime.timedelta(seconds=duration)).split(".")[0]
    human_readable_total = str(datetime.timedelta(seconds=total_time)).split(".")[0]
    await ctx.respond(
        f"{user_name} spent {human_readable_duration} studying!\nTheir total time for the week is now {human_readable_total}"
    )


####################### Competition ###########################


@bot.slash_command(
    description="Add a new activity. Optionally declare whether activity can be done multiple times by same person."
)
async def addactivity(
    ctx,
    name: discord.Option(
        str,
        required=True,
        description="Name of the activity as a past tense verb, e.g. 'uploaded test to file system'",
    ),
    description: discord.Option(
        str, required=True, description="Describe the task in detail"
    ),
    value: discord.Option(
        int,
        required=True,
        description="How many points is the activity worth (put a negative number if it subtracts points)",
    ),
    can_stack: discord.Option(
        bool,
        description="Whether or not the activity can be done multiple times for the same person",
        default=True,
    ),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    newItem = {"description": description, "value": value, "canStack": can_stack}
    if isActivitiesEmpty():
        activities = {name: newItem}
        dumpActivities(activities)
    else:
        activities = loadActivities()
        if name in activities:
            await ctx.respond(f"There is already an activity called '{name}'!")
            return
        activities[name] = newItem
        dumpActivities(activities)
    embed = discord.Embed(title=name, color=discord.Colour.blurple())
    embed.add_field(
        name=(
            f"**{value}** points" if can_stack else f"**{value}** points, non-stackable"
        ),
        value=description,
        inline=False,
    )
    await ctx.respond("Successfully created new activity!", embed=embed)


@bot.slash_command(
    description="Remove an activity from valid activities. This could mess things up."
)
async def removeactivity(
    ctx,
    name: discord.Option(
        str,
        required=True,
        description="Name of the activity to be removed. If unsure, use '/seeactivites' to see a list of activities.",
        autocomplete=getActivityAutocomplete,
    ),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if isActivitiesEmpty():
        await ctx.respond("There are no activities. Something is definitely wrong.")
        return
    activities = loadActivities()
    if name not in activities:
        await ctx.respond(
            f"There is no task called '{name}'. Are you sure that the name you entered is completely correct?"
        )
    activities.pop(name)
    dumpActivities(activities)
    await ctx.respond(f"Activity '{name}' was successfully removed!")


@bot.slash_command(
    description="Modify an activity. Pick one or all of optional params to change. This could mess things up."
)
async def modifyactivity(
    ctx,
    name: discord.Option(
        str,
        required=True,
        description="Name of the activity to be changed. If unsure, use '/seeactivites' to see a list of activities.",
        autocomplete=getActivityAutocomplete,
    ),
    new_description: discord.Option(
        str, required=False, description="New description", default=None
    ),
    new_value: discord.Option(
        int, required=False, description="New value", default=None
    ),
    new_can_stack: discord.Option(
        bool,
        required=False,
        description="Redefine whether the activity can be completed multiple times by one person",
        default=None,
    ),
    new_name: discord.Option(str, required=False, description="New name", default=None),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if isActivitiesEmpty():
        await ctx.respond("There are no activities. Something is definitely wrong.")
        return
    activities = loadActivities()
    if name not in activities:
        await ctx.respond(
            f"There is no task called '{name}'. Are you sure that the name you entered is completely correct?"
        )
    activity = activities[name]
    if new_description is not None:
        activity["description"] = new_description
    if new_value is not None:
        activity["value"] = new_value
        if not isCompetitorsEmpty():
            competitors = loadCompetitors()
            for competitor in competitors.values():
                if name in competitor["activities"]:
                    oldTotal = (
                        competitor["activities"][name] * activities[name]["value"]
                    )
                    newTotal = competitor["activities"][name] * new_value
                    competitor["activities"][name] = (
                        competitor["activities"][name] - oldTotal + newTotal
                    )
            dumpCompetitors(competitors)
    if new_can_stack is not None:
        activity["canStack"] = new_can_stack
        if not new_can_stack and not isCompetitorsEmpty():
            competitors = loadCompetitors()
            for user_id, data in competitors.items():
                if name in data["activities"] and data["activities"][name] > 1:
                    await ctx.send(
                        f"{getName(bot.get_user(int(user_id)))} has already completed multiple of this activity. I would check in on that"
                    )
    if new_name is not None:
        activities[new_name] = activities[name]
        activities.pop(name)
        activity = activities[new_name]
        if not isCompetitorsEmpty():
            competitors = loadCompetitors()
            for competitor in competitors.values():
                if name in competitor["activities"]:
                    competitor["activities"][new_name] = competitor["activities"][name]
                    competitor["activities"].pop(name)
            dumpCompetitors(competitors)
    dumpActivities(activities)
    embed = discord.Embed(
        title=name if new_name is None else new_name, color=discord.Colour.blurple()
    )
    embed.add_field(
        name=(
            f"**{activity['value']}** points"
            if activity["canStack"]
            else f"**{activity['value']}** points, non-stackable"
        ),
        value=activity["description"],
        inline=False,
    )
    await ctx.respond(
        f"**{name}** has been changed! Here is the new activity:", embed=embed
    )


@bot.slash_command(description="See a list of activities")
async def seeactivities(ctx):
    if isActivitiesEmpty():
        await ctx.respond("There are no activities. Something is definitely wrong.")
        return
    activities = loadActivities()
    embeds = list()
    embeds.append(
        discord.Embed(
            title="**Activities**",
            color=discord.Colour.blurple(),
        )
    )
    fields = 1
    for name, props in activities.items():
        if fields % 25 == 0:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
        embeds[len(embeds) - 1].add_field(
            name=f"{name} | *{props['value']} points{', non-stackable' if not props['canStack'] else ''}*",
            value=props["description"],
            inline=False,
        )
        fields += 1
    for embed in embeds:
        await ctx.respond(embed=embed)


@bot.slash_command(description="Make a team with a team leader")
async def makegroup(
    ctx,
    leader: discord.Option(
        discord.Member, required=True, description="Which user will lead this group"
    ),
    group_name: discord.Option(
        str, required=True, description="What will be the name for this group?"
    ),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    newMember = {"activities": {}, "group": group_name, "isLeader": True, "points": 0}
    user_id = str(leader.id)
    if isCompetitorsEmpty():
        member = {user_id: newMember}
        dumpCompetitors(member)
    else:
        competitors = loadCompetitors()
        if user_id in competitors:
            if competitors[user_id]["isLeader"] == True:
                await ctx.respond(
                    f"{getName(leader)} is already leader of the group '{competitors[user_id]['group']}'"
                )
                return
            competitors[user_id]["group"] = group_name
            competitors[user_id]["isLeader"] = True
        else:
            competitors[user_id] = newMember
        dumpCompetitors(competitors)
    await ctx.respond(f"Group '{group_name}' made with {getName(leader)} as leader!")


@bot.slash_command(description="Add a member to a group")
async def addmember(
    ctx,
    user: discord.Option(
        discord.Member, required=True, description="User to add to group"
    ),
    group_name: discord.Option(
        str,
        required=True,
        description="Name of the group for the member to join",
        autocomplete=getGroupAutocomplete,
    ),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if isCompetitorsEmpty():
        await ctx.respond("There is no group by that name! (There are no competitors)")
        return
    competitors = loadCompetitors()
    user_id = str(user.id)
    if user_id in competitors:
        await ctx.respond(
            f"{getName(user)} is already in group '{competitors[user_id]['group']}'"
        )
        return
    if group_name not in getGroupNames():
        await ctx.respond(f"There is no group named '{group_name}'")
        return
    competitors[user_id] = {
        "activities": {},
        "group": group_name,
        "isLeader": False,
        "points": 0,
    }
    dumpCompetitors(competitors)
    await ctx.respond(f"{getName(user)} has been added to group '{group_name}'")


@bot.slash_command(description="List study groups and their members")
async def listgroups(ctx):
    if isCompetitorsEmpty():
        await ctx.respond("There are no groups")
        return
    competitors = loadCompetitors()
    groups = {}
    for user_id, data in competitors.items():
        user = bot.get_user(int(user_id))
        if data["group"] not in groups:
            groups[data["group"]] = [getName(user)]
        else:
            groups[data["group"]].append(getName(user))
    embeds = list()
    for group, members in groups.items():
        embeds.append(
            discord.Embed(
                title=f"**{group}**",
                color=discord.Colour.blurple(),
            )
        )
        for member in members:
            embeds[len(embeds) - 1].add_field(name="", value=member, inline=False)
    for embed in embeds:
        await ctx.respond(embed=embed)


@bot.slash_command(description="See competition stats for an individual")
async def stats(
    ctx,
    user: discord.Option(
        discord.Member, required=True, description="Who's stats you want to check"
    ),
):
    if isCompetitorsEmpty():
        await ctx.respond("There are no competitors")
        return
    competitors = loadCompetitors()
    user_id = str(user.id)
    if user_id not in competitors:
        await ctx.respond(f"{getName(user)} is not in any record")
        return
    compActivities = competitors[user_id]["activities"]
    if isActivitiesEmpty():
        await ctx.respond("There are no activities")
        return
    activities = loadActivities()
    embeds = list()
    embeds.append(
        discord.Embed(
            title=f"**{getName(user)}** | {competitors[user_id]['points']} total points",
            color=discord.Colour.blurple(),
        )
    )
    fields = 1
    for name, count in compActivities.items():
        if fields % 25 == 0:
            embeds.append(discord.Embed(color=discord.Colour.blurple()))
        if name not in activities:
            if name[:3] == "SUB" or name[:3] == "ADD":
                try:
                    points = int(name[3 : name.find(":")])
                    actName = name[(name.find(":") + 1) :]
                except:
                    await ctx.send(f"Activity '{name}' not recognized")
                    continue
                if name[:3] == "SUB":
                    points *= -1
            else:
                await ctx.send(f"Activity '{name}' not recognized")
                continue
        else:
            points = activities[name]["value"]
            actName = name
        embeds[len(embeds) - 1].add_field(
            name=actName if count == 1 else f"{actName} (x{count})",
            value=(
                f"{points} points"
                if count == 1
                else f"{points * count} points ({points} x {count})"
            ),
            inline=False,
        )
        fields += 1
    for embed in embeds:
        await ctx.respond(embed=embed)


@bot.slash_command(description="See competition stats for a group")
async def groupstats(
    ctx,
    group: discord.Option(
        str,
        required=True,
        description="Name of the group to check the stats of",
        autocomplete=getGroupAutocomplete,
    ),
):
    if isCompetitorsEmpty():
        await ctx.respond("There are no competitors")
        return
    competitors = loadCompetitors()
    members = []
    leader = ""
    totalPoints = 0
    for user_id, data in competitors.items():
        if data["group"] == group:
            if data["isLeader"]:
                leader = user_id
            else:
                members.append(user_id)
            totalPoints += data["points"]
    if leader == "":
        await ctx.respond(f"Group '{group}' has no leader")
        return
    teamPoints = int(totalPoints / (len(members) + 1))
    embed = discord.Embed(
        title=f"**{group}** | {teamPoints} team points",
        color=discord.Colour.blurple(),
    )
    embed.add_field(
        name=f"{getName(bot.get_user(int(leader)))} (Leader)",
        value=f"{competitors[leader]['points']} points",
        inline=False,
    )
    for member in members:
        user = bot.get_user(int(member))
        embed.add_field(
            name=getName(user),
            value=f"{competitors[member]['points']} points",
            inline=False,
        )
    await ctx.respond(embed=embed)


@bot.slash_command(description="See competition group leaderboard")
async def leaderboard(ctx):
    if isCompetitorsEmpty():
        await ctx.respond("There are no competitors")
        return
    competitors = loadCompetitors()
    groups = {}
    for user_id, data in competitors.items():
        if data["group"] not in groups:
            groups[data["group"]] = [user_id]
        else:
            groups[data["group"]].append(user_id)
    groupPoints = {}
    for group, members in groups.items():
        totalPoints = 0
        for member in members:
            totalPoints += competitors[member]["points"]
        teamPoints = totalPoints / len(members)
        groupPoints[group] = int(teamPoints)
    embed = discord.Embed(title="Leaderboard", color=discord.Colour.blurple())
    place = 1
    for group, points in dict(
        sorted(groupPoints.items(), key=lambda item: item[1], reverse=True)[:24]
    ).items():
        embed.add_field(
            name=f"{place}. {group}", value=f"{points} team points", inline=False
        )
        place += 1
    await ctx.respond(embed=embed)


@bot.slash_command(description="See competition top 10 individuals leaderboard")
async def sololeaderboard(ctx):
    if isCompetitorsEmpty():
        await ctx.respond("There are no competitors")
        return
    competitors = loadCompetitors()
    compPoints = {}
    for user_id, data in competitors.items():
        compPoints[user_id] = data["points"]
    embed = discord.Embed(title="Solo Leaderboard", color=discord.Colour.blurple())
    place = 1
    for user_id, data in dict(
        sorted(compPoints.items(), key=lambda item: item[1], reverse=True)[:10]
    ).items():
        embed.add_field(
            name=f"{place}. {getName(bot.get_user(int(user_id)))}",
            value=f"{competitors[user_id]['points']} points",
            inline=False,
        )
        place += 1
    await ctx.respond(embed=embed)


@bot.slash_command(description="Mark an activity as complete for a user")
async def completeactivity(
    ctx,
    user: discord.Option(
        discord.Member, required=True, description="Which user completed the activity"
    ),
    activity: discord.Option(
        str,
        required=True,
        description="What activity did they complete",
        autocomplete=getActivityAutocomplete,
    ),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if isCompetitorsEmpty() or isActivitiesEmpty():
        await ctx.respond("Something is wrong with competitor or activity data")
        return
    user_id = str(user.id)
    competitors = loadCompetitors()
    activities = loadActivities()
    if user_id not in competitors:
        await ctx.respond(f"{getName(user)} is not a competitor")
        return
    competitor = competitors[user_id]
    if activity not in activities:
        await ctx.respond(f"Activity '{activity}' is not a valid activity")
        return
    if activity in competitor["activities"]:
        if activities[activity]["canStack"] == False:
            await ctx.respond(
                f"Activity '{activity}' can only be completed once per person"
            )
            return
        competitor["activities"][activity] += 1
    else:
        competitor["activities"][activity] = 1
    competitor["points"] += activities[activity]["value"]
    competitors[user_id] = competitor
    dumpCompetitors(competitors)
    await ctx.respond(
        f"{getName(user)} has completed '{activity}' and now has {competitor['points']} points!"
    )


@bot.slash_command(description="Remove an activity from a user")
async def uncompleteactivity(
    ctx,
    user: discord.Option(
        discord.Member,
        required=True,
        description="Which user wrongfully completed the activity",
    ),
    activity: discord.Option(
        str,
        required=True,
        description="What activity did they not complete",
        autocomplete=getUserActivityAutocomplete,
    ),
    points: discord.Option(
        int,
        required=False,
        description="In case activity point value can't be found, specify value to subtract",
    ),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if isCompetitorsEmpty() or isActivitiesEmpty():
        await ctx.respond("Something is wrong with competitor or activity data")
        return
    user_id = str(user.id)
    competitors = loadCompetitors()
    activities = loadActivities()
    if activity not in competitors[user_id]["activities"]:
        await ctx.respond(f"{getName(user)} has not completed activity '{activity}'")
        return
    value = 0
    if activity not in activities:
        if activity[:3] == "ADD" or activity[:3] == "SUB":
            try:
                pts = int(activity[3 : activity.find(":")])
            except:
                await ctx.send(f"Activity '{activity}' not recognized")
                return
            if activity[:3] == "SUB":
                pts *= -1
            value = pts
        elif points is None:
            await ctx.respond(
                "Can not find activity. Check activity name or specify value to subtract"
            )
            return
        else:
            value = points
    else:
        value = activities[activity]["value"]
    if competitors[user_id]["activities"][activity] == 1:
        competitors[user_id]["activities"].pop(activity)
    else:
        competitors[user_id]["activities"][activity] -= 1
    competitors[user_id]["points"] -= value
    dumpCompetitors(competitors)
    await ctx.respond(
        f"{getName(user)} has no longer completed '{activity}' and now has {competitors[user_id]['points']} points!"
    )


@bot.slash_command(description="Add points to a user without an activity")
async def addpoints(
    ctx,
    user: discord.Option(discord.Member, required=True, description="Who to add to"),
    points: discord.Option(int, required=True, description="How many points to add"),
    reason: discord.Option(str, required=True, description="Why"),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if isCompetitorsEmpty():
        await ctx.respond("There are no competitors")
        return
    competitors = loadCompetitors()
    user_id = str(user.id)
    if user_id not in competitors:
        await ctx.respond(f"{getName(user)} is not a competitor")
        return
    activity = f"ADD{points}:{reason}"
    if activity in competitors[user_id]["activities"]:
        competitors[user_id]["activities"][activity] += 1
    else:
        competitors[user_id]["activities"][activity] = 1
    competitors[user_id]["points"] += points
    dumpCompetitors(competitors)
    await ctx.respond(f"Added {points} points to {getName(user)}")


@bot.slash_command(description="Subtract points from a user")
async def subtractpoints(
    ctx,
    user: discord.Option(
        discord.Member, required=True, description="Who to subtract from"
    ),
    points: discord.Option(
        int, required=True, description="How many points to subtract"
    ),
    reason: discord.Option(str, required=True, description="Why"),
):
    if not is_admin(ctx.author):
        await ctx.respond("You don't have permission for this command")
        return
    if isCompetitorsEmpty():
        await ctx.respond("There are no competitors")
        return
    competitors = loadCompetitors()
    user_id = str(user.id)
    if user_id not in competitors:
        await ctx.respond(f"{getName(user)} is not a competitor")
        return
    activity = f"SUB{points}:{reason}"
    if activity in competitors[user_id]["activities"]:
        competitors[user_id]["activities"][activity] += 1
    else:
        competitors[user_id]["activities"][activity] = 1
    competitors[user_id]["points"] -= points
    dumpCompetitors(competitors)
    await ctx.respond(f"Subtracted {points} points from {getName(user)}")


########################## Tasks ##############################


# check if a user is in voice chat (and sharing screen) and @ them if they are not
# currently bases channel / guild off context. I don't think this will be an issue right now but it might be in the future
# could also look into seperate tasks/coroutines per person and not have to do so much iterating (discord won't let you have multiple task instances to my knowledge)
# could also look into adding persistence (not a big deal, only matters if bot restarts and nobody else starts after)
@tasks.loop(minutes=15)
async def check_vc(ctx):
    guild = ctx.guild
    members = await guild.fetch_members(limit=None).flatten()
    currentReviewStudiers = list()
    for m in members:
        if (
            is_review(m)
            and cur.execute(
                "SELECT session_id FROM sessions WHERE user_id = (?) AND is_complete = 0",
                (int(m.id),),
            ).fetchone()
        ):
            currentReviewStudiers.append(m)
    if not currentReviewStudiers:
        check_vc.stop()
        return
    noVc = []
    noStream = []
    for studier in currentReviewStudiers:
        voice_state = studier.voice
        if voice_state is None:
            noVc.append(studier)
        elif not voice_state.self_stream:
            noStream.append(studier)
    vcString = ""
    for studier in noVc:
        vcString += f"<@{studier.id}> "
    if vcString != "":
        await ctx.send(
            f"{vcString}make sure that you're in the **Study hours** channel!"
        )
    streamString = ""
    for studier in noStream:
        streamString += f"<@{studier.id}> "
    if streamString != "":
        await ctx.send(f"{streamString}make sure that you're sharing your screen!")


# send a message to people with long sessions (defined by LONG_TIME constant) asking if they are still there
# could definitely find a more elegant solution (coroutines)
@tasks.loop(hours=2)
async def check_long(ctx):
    guild = ctx.guild
    members = await guild.fetch_members(limit=None).flatten()
    longStudiers = list()
    currentTime = datetime.datetime.now().timestamp() - 18000  # current time in seconds
    longStartTime = currentTime - LONG_TIME  # latest time which is long (in seconds)
    for m in members:
        startTime = cur.execute(
            "SELECT start_time FROM sessions WHERE user_id = (?) AND is_complete = 0",
            (int(m.id),),
        ).fetchone()
        if startTime and startTime[0] < longStartTime:
            longStudiers.append((m, startTime[0]))
    for studySession in longStudiers:
        duration = currentTime - studySession[1]
        await ctx.send(
            f"<@{studySession[0].id}> you've been studying for over {int(duration/3600)} hours! Are you still there?"
        )  # make single message for multiple (on check_vc too)


# does not work right now idk what's wrong with the time param ):
@tasks.loop(time=DAILY_CHECK_TIME)
async def daily_check():
    channel = bot.get_channel(CHANNEL_ID)  # remove when check messages aren't necessary

    weekNum = datetime.datetime.today().weekday()  # starting at 6 (sunday)
    if weekNum == 6:  # sunday
        CHANNEL_ID.send("sunday")
    elif weekNum == 7:  # monday
        CHANNEL_ID.send("monday")
    elif weekNum == 1:  # tuesday
        channel.send("tuesday")
        check_progress(0)
    elif weekNum == 2:  # wednesday
        channel.send("wednesday")
        check_progress(0)
    elif weekNum == 3:  # thursday
        channel.send("thursday")
        check_progress(33)
    elif weekNum == 4:  # friday
        channel.send("friday")
        check_progress(50)
    elif weekNum == 5:  # saturday
        channel.send("saturday")
        check_progress(100)


async def check_progress(percent: int):
    guild = await client.fetch_guild(SERVER_ID)
    members = await guild.fetch_members(limit=None).flatten()
    channel = bot.get_channel(CHANNEL_ID)
    flagList = []
    for member in members:
        if is_studier(member):
            tup = cur.execute(
                f"SELECT total_time, required_hours FROM studiers WHERE user_id = (?)",
                (member.id,),
            ).fetchone()
            if not tup or tup[0] / tup[1] < percent / 100:
                flagList.append(member.id)
    flagsString = ""
    for user_id in flagList:
        flagsString += f"<@{user_id}> "
    if flagsString != "":
        if ratio == 0:
            channel.send(
                f"{flagsString}make sure that you are getting your hours in. You all have no hours so far this week."
            )
        elif ratio == 1:
            channel.send(
                f"{flagString}make sure that you are getting your hours in before the end of the week."
            )
        else:
            channel.send(
                f"{flagsString}make sure that you are getting your hours in. You all have less than {percent}% of your hours so far this week."
            )


###start bot
bot.run(BOT_TOKEN)


# TODO list
# daily routine - ping people who are behind, clear at end of week, call report weekly - check that its working and change time to like 3am, add clear - time not working idk why
# help function - user and admin - made but make sure it stays accurate
# make code cleaner - functions for permission check, existence check, finding username, etc. - do not need f strings for queries (usually) - modularize!!!? - make single function with parameter to specify prev? - seperate files for hours / comp / utils?
# track classes?
# make activesessions able to handle > 25 (like serverreport and userreport do)
# long term study hour storage - store hours per week
# only study 6-11 for academic review - routine to stop them at 11 and check on start that its between 6 and 11, besides weekends?
# cogs to group commands
# steal for competition (catch someone skipping class)
# setters for constants? modular function
# view report by study group
# error messages?
