# This program checks if members with a special role are chatting in the server, if they're not chatting for some amount of time (afkTime), their role will be removed.
# For this, I'm going to create a database and whenever a message is sent, I'm going to store it with the user D

import discord, aiosqlite, yaml, datetime
from discord.ext import commands, tasks
from rich import print, console

# -- Constants -- #

console = console.Console()
with open("config.yml", "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
bot = commands.Bot(
    command_prefix=config["prefix"],
    case_insensitive=True,
    intents=discord.Intents.all(),
)
whitelistedRole = int(config["whitelistedRole"])
afkTime = int(config["afkTime"])
# Convert AFK time to seconds
afkTime = afkTime * 60
giveRole = (config["giveRole"], config["giveRoleID"])
databasePath = "database.db"

# -- Functions -- #


async def readyDatabase():
    async with aiosqlite.connect(databasePath) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            lastMessageTime INTEGER NOT NULL)
            """
        )
        await db.commit()
    console.log("Database ready.")
    return True


async def addMessage(message):
    async with aiosqlite.connect(databasePath) as db:
        # Insert or update
        await db.execute(
            """INSERT OR REPLACE INTO users(id, lastMessageTime) VALUES(?, ?)""",
            (message.author.id, message.created_at),
        )
        await db.commit()
    # console.log(f"{message.author.name}'s message added to database.")
    return True


async def checkUser(user):
    async with aiosqlite.connect(databasePath) as db:
        cursor = await db.execute(
            """SELECT lastMessageTime FROM users WHERE id = ?""", (user.id,)
        )
        lastMessageTime = await cursor.fetchone()
        await cursor.close()

    if lastMessageTime is None:
        # console.log(f"{user.name}'s message not found in database.")
        return False
    else:
        lastMessageTime = datetime.datetime.strptime(
            lastMessageTime[0], "%Y-%m-%d %H:%M:%S.%f"
        )
        if datetime.datetime.now() - lastMessageTime > datetime.timedelta(
            seconds=afkTime
        ):
            console.log(f"{user.name}'s message found in database, but they're afk.")
            return True


@bot.listen()
async def on_ready():
    """Event: on_ready"""
    console.log(
        f"Connected to Discord Socket as {bot.user} (ID: {bot.user.id}) and in {len(bot.guilds)} guilds.\n\nGuilds - \n- "
        + "\n- ".join(
            [
                f"{guild.name} ({guild.id}) - {guild.member_count} Members"
                for guild in bot.guilds
            ]
        )
        + "\n----------------\n"
    )
    print(f"Connected as {bot.user} and in {len(bot.guilds)} guilds.")
    print("----------------")
    await readyDatabase()


@bot.listen()
async def on_message(message):
    """Event: on_message"""
    if message.author.bot:
        return
    if message.guild is not None:
        await addMessage(message)
    else:
        console.log(f"{message.author.name}'s message not added to database.")


@tasks.loop(minutes=10)
async def heckAFK():
    await bot.wait_until_ready()
    console.log("Checking for AFK users...")

    # Create a dict of {guild Object : [member object of users with whitelisted role]}
    whitelistedUsers = {}
    for guild in bot.guilds:
        whitelistedUsers[guild] = []
        for member in guild.members:
            if whitelistedRole in [role.id for role in member.roles]:
                whitelistedUsers[guild].append(member)

    for guild, members in whitelistedUsers.items():
        role = guild.get_role(whitelistedRole)
        toGive = guild.get_role(giveRole[1])
        if role is None:
            continue
        for member in members:
            if await checkUser(member):
                await member.remove_roles(role)
                if giveRole[0]:
                    await member.add_roles(toGive)


# -- Running -- #
heckAFK.start()
bot.run(config["token"])

# am dead inside ✨, will probably rewrite later as code quality isn't the best