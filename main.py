"""
================================================================================
                           F1 DISCORD BOT - WORKSPACE  
================================================================================

This bot is a fully-featured Discord Bot that integrates with the FastF1 library
and Ergast API to provide users with Formula 1 standings, calendars, race results,
driver comparisons, fastest laps, and detailed countdowns for upcoming race weekends.

--------------------------------------------------------------------------------
PROJECT FILE STRUCTURE & USES
--------------------------------------------------------------------------------
1. main.py (This File)
   - The main entry point of the application.
   - Sets up the Discord bot with necessary intents (message content, members, presences).
   - Establishes log files using the `logging` module to keep track of debug messages.
   - Implements event listeners (e.g., bot ready state, member join notifications).
   - Defines a variety of Discord prefix commands (!) grouped into:
     - Utility/General Commands (hello, assign, remove, dm, reply, poll, download).
     - Formula 1 commands (champ, const, results, fastest, calendar, compare, circuit, raceweekend, drivers).
     - Role-restricted commands (secret).

2. requirements.txt
   - Specifies the list of Python dependencies required to run the bot:
     - discord.py: The API wrapper for Discord.
     - python-dotenv: Loads secret variables from a .env file into environment variables.
     - fastf1: A library for F1 telemetry, session results, and schedule details.
     - pandas: Handles data analysis and tabular data manipulation for standings/schedules.
     - pytz: Handles time zones and localization (converting UTC times to local times).
     - aiohttp: Asynchronous HTTP requests.

3. Procfile (not done dont even remember where I even reached )
   - A configuration file used by hosting/deployment platforms (such as Heroku)
     to run the bot as a background worker process.
   - Declares the process type and entry command: `worker: python main.py`.

4. .env
   - Houses the `DISCORD_TOKEN` secret key required for authenticating the bot with the Discord API.
   - Excluded from version control for security purposes.

5. discord.log (Generated at runtime)
   - Created automatically when the bot runs.
   - Contains log outputs to debug operations and record warnings/errors.

6. f1_cache / fastf1_cache (Generated at runtime)
   - Directories created by fastf1's caching system to speed up data lookup and prevent API rate-limiting.

--------------------------------------------------------------------------------
WHY GIT & VERSION CONTROL ARE CRITICAL
--------------------------------------------------------------------------------
Using Git and version control systems is highly recommended for developers:
- **Credential Protection**: With Git, we configure a `.gitignore` file to ensure
  sensitive configuration files like `.env` are never uploaded to public servers
  (e.g., GitHub), preventing credentials leakage.
- **Collaborative Flow**: Facilitates team coordination without overwriting
  each other's edits, using branches and pull requests.
- **History Rollback**: Acts as a time-machine allowing developers to view
  historical changes, compare lines, and restore the codebase to a stable state
  if a feature breaks.

--------------------------------------------------------------------------------
KEY VARIABLES USED & THEIR DESCRIPTIONS
--------------------------------------------------------------------------------
- token (str): Stores the secret Discord API Token fetched from the environment.
- handler (logging.FileHandler): Outputs all logging stream entries to discord.log.
- intents (discord.Intents): Configures event tracking filters requested from Discord.
- bot (commands.Bot): The interactive client application connecting with the Discord API.
- secret_role (str): Specifies the required role name ("Gamer") for private commands.
- tz_local (pytz.timezone): Stores the user timezone ("America/Port_of_Spain") for calendars.
- schedule (pd.DataFrame): Holds the complete schedule list returned from FastF1.
- next_event (pd.Series): Holds row details for the upcoming Grand Prix weekend.
- country_flag (str): Emoji flag character mapped from the race country.
- is_sprint (bool): Flags if the weekend schedule features F1 sprint race sessions.
- session_names (list): Holds F1 session titles based on the event layout.
- session_keys (list): Maps session attributes to their fastf1 schedule column keys.
- session_list (list): Holds a collection of (session_name, session_time) tuples.
- next_session_index (int): Keeps track of the index of the next active session.
- message (discord.Message): Reference to the Discord message undergoing dynamic edits.
- key / name (str): Multi-use search/loop key variables for parsing datasets.
  * What is parsing datasets? In this context, it refers to taking raw, structured tables of F1 data (like schedules, 
  constructor standings, or telemetry from FastF1/Ergast DataFrames) and extracting, sorting, or translating specific parts 
  (such as session times or country codes) so they can be neatly displayed in Discord messages and embeds.

--------------------------------------------------------------------------------
LIBRARIES & APIS USED
--------------------------------------------------------------------------------
- discord.py (v2+): Asynchronous library for interacting with Discord.
- FastF1 & Ergast API: Used to fetch live F1 timing data, telemetry, and historic statistics.
- Python Logging: Outputs debug streams to `discord.log`.
- Asyncio: Runs long-running blocking calls asynchronously in separate threads to keep the bot responsive.
- flag (unused but imported): Utility to translate country codes to emoji flags.

================================================================================
"""

# ==============================================================================
#                               SYSTEM IMPORTS
# ==============================================================================
import asyncio                 # Used for handling asynchronous operations, timers, and sleeping
import logging                 # Used to record bot activity, warnings, and errors in a file
import os                      # Used to access local environment variables and filesystem details
from datetime import datetime  # Used for handling current dates, session schedules, and timestamps
import pytz                    # Used for timezone conversions and localized countdown calculations

# ==============================================================================
#                            THIRD-PARTY IMPORTS
# ==============================================================================
import discord                 # The main library wrapper for the Discord API
from discord.ext import commands  # Sub-package facilitating command creation and prefix handling
import fastf1                  # F1 library to fetch schedule details, telemetry, and session results
import pandas as pd            # Data manipulation library used to sort and filter standings and calendars
import flag                    # Utility package to transform country codes into flag emojis
import aiohttp                 # Asynchronous HTTP client (available for background network operations)
from dotenv import load_dotenv  # Loads variables from .env to secure credentials

# ==============================================================================
#                            BOT CONFIGURATION
# ==============================================================================

# Enable local caching for the FastF1 library. 
# Telemetry files are heavy, so caching prevents rate-limits and speeds up responses.
fastf1.Cache.enable_cache("f1_cache")

# Load environment variables from the local .env configuration file
load_dotenv()

# Fetch the Discord bot token from environment variables
token = os.getenv('DISCORD_TOKEN')

# Initialize a file-based log handler pointing to 'discord.log'.
# Overwrites ('w') the file on startup and uses UTF-8 encoding.
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
# Got this from the Discord site man sum so
# Set up Gateway Intents. Intents specify what events Discord sends to the bot.
intents = discord.Intents.default()
intents.message_content = True  # Allows reading message content (required for prefix commands)
intents.members = True          # Allows handling member events (e.g., when a user joins)
intents.presences = True        # Allows the bot to monitor user presence states (online/offline)

# Create the bot instance using '!' as the prefix for all text commands
bot = commands.Bot(command_prefix='!', intents=intents)

# Specify a role name that will be required to execute restricted/secret commands
# This shit means jack
secret_role = "Gamer"


# ==============================================================================
#                                EVENT HANDLERS
# ==============================================================================

@bot.event
async def on_ready():
    """
    Event listener triggered when the bot successfully logs in,
    completes caching internal guild structures, and becomes ready.
    """
    print(f"We are ready to go in, {bot.user.name}")


@bot.event
async def on_member_join(member):
    """
    Event listener triggered when a new user joins the Discord server.
    Automatically sends a welcome greeting to the user's direct messages (DMs).
    """
    await member.send(f"Welcome to the server {member.name}")


# Example of a message filter (currently commented out)
# It listens to all messages and deletes ones that contain bad words
#
# @bot.event
# async def on_message(message):
#     # Ignore messages sent by the bot itself to prevent infinite loops
#     if message.author == bot.user:
#         return
#
#     # Simple profanity filter example
#     if "shit" in message.content.lower():
#         await message.delete()
#         await message.channel.send(f"{message.author.mention} - don't use that word!")
#
#     # IMPORTANT: Explicitly process commands because overriding on_message
#     # halts default command processing by default.
#     await bot.process_commands(message)


# ==============================================================================
#                            GENERAL UTILITY COMMANDS
# ==============================================================================

@bot.command()
async def hello(ctx):
    """
    A simple greeting command.
    Usage: !hello
    Responds by mentioning the user who triggered the command.
    """
    await ctx.send(f"Hello {ctx.author.mention}!")


@bot.command()
async def assign(ctx, role: discord.Role, to: str, member: discord.Member):
    """
    Assigns a specified role to a member.
    Usage: !assign @Role to @User
    
    Parameters:
      - role: The Discord role object to assign.
      - to: A validation string (must literally match 'to').
      - member: The target server member receiving the role.
    """
    # Verify the syntax contains the connector keyword 'to'
    if to.lower() != "to":
        await ctx.send("Invalid syntax! Use: `!assign @role to @user`")
        return
    
    try:
        # Asynchronously assign the role to the target user
        await member.add_roles(role)
        await ctx.send(f"✅ Successfully assigned **{role.name}** to **{member.display_name}**")
    except discord.Forbidden:
        # Fails if the bot role's hierarchy position is lower than the target role
        await ctx.send("❌ I don't have permission to assign that role. (Hint: Move my bot role higher in the settings!)")
    except Exception as e:
        # Handle and log generic errors
        await ctx.send(f"❌ An error occurred: {e}")


@bot.command()
async def remove(ctx, role: discord.Role, From: str, member: discord.Member):
    """
    Removes a specified role from a member.
    Usage: !remove @Role from @User
    
    Parameters:
      - role: The Discord role object to remove.
      - From: A validation string (must literally match 'from').
      - member: The target server member losing the role.
    """
    # Verify the syntax contains the connector keyword 'from'
    if From.lower() != "from":
        await ctx.send("Invalid syntax! Use: `!remove @role from @user`")
        return

    try:
        # Asynchronously remove the role from the target user
        await member.remove_roles(role)
        await ctx.send(f"✅ Successfully removed **{role.name}** from **{member.display_name}**")
    except discord.Forbidden:
        # Fails if the bot's permission levels do not allow managing this role
        await ctx.send("❌ I don't have permission to remove that role.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")


@bot.command()
async def dm(ctx, member: discord.Member, *, msg):
    """
    Sends a direct message (DM) to a specific user.
    Usage: !dm @User <message content>
    
    Parameters:
      - member: The target member to DM.
      - msg: The text content of the message (captures all trailing arguments).
    """
    try:
        # Send message directly to target user
        await member.send(msg)
        await ctx.send(f"📬 Sent a DM to **{member.display_name}**")
    except discord.Forbidden:
        # Fails if the user blocked the bot or has their server DMs locked
        await ctx.send(f"🚫 I couldn't DM **{member.display_name}**. They might have their DMs closed.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")


@bot.command()
async def reply(ctx):
    """
    Replies directly to the user's message using Discord's inline reply formatting.
    Usage: !reply
    """
    await ctx.reply("This is a reply to your message!")


@bot.command()
async def poll(ctx, *, question):
    """
    Creates a simple yes/no interactive poll using reaction emojis.
    Usage: !poll Should we play games tonight?
    
    Parameters:
      - question: The query/prompt for the poll.
    """
    # Construct poll details in an embed structure
    embed = discord.Embed(title="New Poll", description=question)
    poll_message = await ctx.send(embed=embed)
    
    # Add reaction options (Thumbs Up and Thumbs Down)
    await poll_message.add_reaction("👍")
    await poll_message.add_reaction("👎")


@bot.command(name="commands", aliases=["command"])
async def list_commands(ctx):
    """
    Displays an interactive list of all registered commands and their descriptions.
    Usage: !commands or !command
    """
    # Setup commands overview embed
    embed = discord.Embed(
        title="Bot Commands",
        description="Here is everything I can do! Use the `!` prefix before each command.",
        color=discord.Color.blue()
    )

    # Loop through all commands registered to the bot instance
    for command in bot.commands:
        # Exclude hidden commands and the default help utility command
        if not command.hidden and command.name != "help":
            description = command.help or "No description provided."
            embed.add_field(
                name=f"**!{command.name}**",
                value=description,
                inline=False
            )

    embed.set_footer(text="Tip: You can also use !help <command> for more details.")
    await ctx.send(embed=embed)


# ==============================================================================
#                            FORMULA 1 BOT COMMANDS
# ==============================================================================

@bot.command()
async def champ(ctx):
    """
    Displays the top 10 drivers in the current F1 Drivers' Championship.
    Usage: !champ
    Queries the Ergast API database.
    """
    try:
        # Define a helper function to perform the synchronous Ergast API fetch
        def get_standings():
            ergast = fastf1.ergast.Ergast()
            return ergast.get_driver_standings(season='current').content[0]
            
        # Run the synchronous fastf1 call in a separate thread to prevent freezing the bot
        df = await asyncio.to_thread(get_standings)
        
        # Verify standings data exists
        if df.empty:
            await ctx.send("🏁 No standings data found for the current season yet.")
            return

        # Setup standings overview embed details
        embed = discord.Embed(
            title="🏆 F1 Drivers' Championship Top 10",
            description="",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        # Parse driver details and design output
        description = ""
        for i, row in df.head(10).iterrows():
            pos = row['position']
            name = f"{row['givenName']} {row['familyName']}"
            points = row['points']
            # Safely extract constructor name if available
            team = row['constructorNames'][0] if len(row['constructorNames']) > 0 else "Unknown"
            
            # Use medals for podium spots
            medal = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f"**{pos}.**"
            description += f"{medal} **{name}** ({team}) — `{points} pts` \n"

        embed.description = description
        embed.set_footer(text="lol")
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f" Error: {e}")


@bot.command()
async def const(ctx):
    """
    Displays the current top 10 constructor/team standings in Formula 1.
    Usage: !const
    """
    try:
        # Helper function to execute Ergast lookup synchronously
        def get_const():
            ergast = fastf1.ergast.Ergast()
            return ergast.get_constructor_standings(season='current').content[0]
            
        # Offload the blocking Ergast network request to a background thread
        df = await asyncio.to_thread(get_const)
        
        if df.empty:
            await ctx.send("🏁 No constructor standings found for the current season yet.")
            return

        # Setup constructor ranking details inside an embed
        embed = discord.Embed(
            title="🏎️ F1 Constructor Standings",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Iterate and build rankings layout
        description = ""
        for i, row in df.head(10).iterrows():
            pos = row['position']
            team = row['constructorName']
            points = row['points']
            wins = row['wins']
            
            # Format list rows
            medal = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f"**{pos}.**"
            description += f"{medal} **{team}** — `{points} pts` ({wins} wins)\n"

        embed.description = description
        embed.set_footer(text="Data provided by FastF1")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error fetching constructor standings: {e}")


@bot.command()
async def results(ctx):
    """
    Shows the race standings of the most recently finished Grand Prix (Top 10).
    Usage: !results
    """
    try:
        # Synchronous function to retrieve recent race placements
        def get_res():
            ergast = fastf1.ergast.Ergast()
            return ergast.get_race_results(season='current', round='last').content[0]
            
        # Execute query in an asynchronous thread context
        df = await asyncio.to_thread(get_res)
        
        if df.empty:
            await ctx.send("🏁 No recent race results found.")
            return

        # Prepare race details output embed
        embed = discord.Embed(
            title="🏁 Last Race Results Top 10",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # Build driver results list
        description = ""
        for i, row in df.head(10).iterrows():
            pos = row['positionText']
            name = f"{row['givenName']} {row['familyName']}"
            team = row['constructorName']
            points = row['points']
            
            description += f"**{pos}.** {name} ({team}) — `+{points} pts`\n"

        embed.description = description
        embed.set_footer(text="Data provided by FastF1")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error fetching race results: {e}")


@bot.command()
async def fastest(ctx):
    """
    Shows the driver who completed the fastest lap of the last race and their time.
    Usage: !fastest
    """
    # Notify the channel that session telemetry files are being downloaded
    msg = await ctx.send("⏳ Fetching telemetry for the last race... This might take a few seconds.")
    try:
        # Load and download session telemetry synchronously
        def get_fastest():
            session = fastf1.get_session('current', 'last', 'R')
            # Load basic session data, ignoring telemetry details to improve response speed
            session.load(telemetry=False, weather=False, messages=False)
            return session.laps.pick_fastest()
            
        # Run loading function off-thread
        lap = await asyncio.to_thread(get_fastest)
        
        # Retrieve fastest lap info
        driver = lap['Driver']
        # Convert Timedelta format into a readable HH:MM:SS or MM:SS format
        time = str(lap['LapTime']).split('.')[0][-8:] 
        
        embed = discord.Embed(
            title="⏱️ Fastest Lap (Last Race)",
            description=f"**Driver:** {driver}\n**Time:** `{time}`",
            color=discord.Color.purple()
        )
        # Edit the status message into the finished embed response
        await msg.edit(content=None, embed=embed)
    except Exception as e:
        await msg.edit(content=f"❌ Error fetching fastest lap: {e}")


@bot.command()
async def calendar(ctx):
    """
    Fetches and displays the next 5 upcoming races in the F1 season.
    Usage: !calendar
    """
    try:
        # Helper function to load current season events
        def get_cal():
            return fastf1.get_event_schedule(datetime.now().year)
            
        schedule = await asyncio.to_thread(get_cal)
        now = datetime.now(pytz.utc)  # Reference UTC date
        
        # Filter schedule for upcoming events
        upcoming = []
        for _, event in schedule.iterrows():
            session_time = event['EventDate']
            if pd.isna(session_time): 
                continue
            
            # Localize native datetime inputs to UTC
            if session_time.tzinfo is None:
                session_time = pytz.utc.localize(session_time)
                
            # If the date is ahead of current time, save it
            if session_time > now:
                upcoming.append(event)
                # Keep only 5 events
                if len(upcoming) == 5:
                    break
                    
        if not upcoming:
            await ctx.send("🏁 No more upcoming races this season.")
            return

        # Prepare calendar schedule embed
        embed = discord.Embed(
            title="📅 Upcoming F1 Races",
            color=discord.Color.blue()
        )
        
        # Populate embed fields with track details
        for event in upcoming:
            date_str = event['EventDate'].strftime("%d %b %Y")
            embed.add_field(
                name=f"Round {event['RoundNumber']}: {event['EventName']}",
                value=f"📍 {event['Location']}, {event['Country']}\n🗓️ {date_str}",
                inline=False
            )
            
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error fetching calendar: {e}")


@bot.command()
async def compare(ctx, driver1: str, driver2: str):
    """
    Compares the current season standings and stats of two drivers.
    Usage: !compare VER HAM
    
    Parameters:
      - driver1: The 3-letter driver code of the first driver.
      - driver2: The 3-letter driver code of the second driver.
    """
    try:
        # Standardize abbreviation inputs to uppercase
        driver1 = driver1.upper()
        driver2 = driver2.upper()
        
        # Sync fetch standings list
        def get_standings():
            ergast = fastf1.ergast.Ergast()
            return ergast.get_driver_standings(season='current').content[0]
            
        # Execute standings retrieval asynchronously
        df = await asyncio.to_thread(get_standings)
        
        # Filter for the rows containing the requested drivers
        d1_row = df[df['driverCode'].str.upper() == driver1]
        d2_row = df[df['driverCode'].str.upper() == driver2]
        
        # Verify both driver codes were successfully found
        if d1_row.empty or d2_row.empty:
            await ctx.send("❌ Could not find one or both drivers. Make sure to use their 3-letter codes (e.g., VER, HAM, LEC).")
            return
            
        d1 = d1_row.iloc[0]
        d2 = d2_row.iloc[0]

        # Structure comparison statistics inside an embed
        embed = discord.Embed(
            title="🔍 Driver Comparison",
            description=f"**Current Season Stats**",
            color=discord.Color.orange()
        )
        
        # Add driver comparison details columns side-by-side
        embed.add_field(
            name=f"{d1['givenName']} {d1['familyName']} ({driver1})",
            value=f"**Position:** {d1['position']}\n**Points:** {d1['points']}\n**Wins:** {d1['wins']}\n**Team:** {d1['constructorNames'][0]}",
            inline=True
        )
        embed.add_field(name="🆚", value="\u200b", inline=True)  # Spacer column
        embed.add_field(
            name=f"{d2['givenName']} {d2['familyName']} ({driver2})",
            value=f"**Position:** {d2['position']}\n**Points:** {d2['points']}\n**Wins:** {d2['wins']}\n**Team:** {d2['constructorNames'][0]}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error comparing drivers: {e}")


@bot.command()
async def circuit(ctx, *, country: str):
    """
    Shows track info for a specific country in the current season calendar.
    Usage: !circuit Italy
    
    Parameters:
      - country: Target host country name.
    """
    try:
        # Helper schedule load function
        def get_cal():
            return fastf1.get_event_schedule(datetime.now().year)
            
        schedule = await asyncio.to_thread(get_cal)
        
        # Search for matching country (case-insensitive search)
        match = schedule[schedule['Country'].str.lower() == country.lower()]
        
        # If no host country matches, reply with error
        if match.empty:
            await ctx.send(f"❌ Could not find a race in `{country}` for this season.")
            return
            
        event = match.iloc[0]
        
        # Prepare track data embed display
        embed = discord.Embed(
            title=f"🛣️ {event['OfficialEventName']}",
            color=discord.Color.teal()
        )
        embed.add_field(name="Location", value=event['Location'], inline=True)
        embed.add_field(name="Country", value=event['Country'], inline=True)
        embed.add_field(name="Round", value=event['RoundNumber'], inline=True)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error fetching circuit info: {e}")


def country_to_emoji(country_name):
    """
    Translates F1 host country names to matching flag emojis using ISO definitions.
    Generates Unicode Regional Indicator symbols from uppercase characters.
    
    Parameters:
      - country_name: String country name.
      
    Returns:
      - A Unicode emoji flag string, or 🏁 as a fallback.
    """
    # Key mapping of F1 calendar countries to ISO country code strings
    COUNTRY_ISO = {
        "australia": "AU",
        "austria": "AT",
        "azerbaijan": "AZ",
        "bahrain": "BH",
        "belgium": "BE",
        "brazil": "BR",
        "canada": "CA",
        "china": "CN",
        "france": "FR",
        "germany": "DE",
        "hungary": "HU",
        "italy": "IT",
        "japan": "JP",
        "mexico": "MX",
        "monaco": "MC",
        "netherlands": "NL",
        "portugal": "PT",
        "qatar": "QA",
        "saudi arabia": "SA",
        "singapore": "SG",
        "south africa": "ZA",
        "spain": "ES",
        "united arab emirates": "AE",
        "uae": "AE",
        "united kingdom": "GB",
        "uk": "GB",
        "united states": "US",
        "usa": "US",
    }

    # Format country inputs for lookups
    key = country_name.strip().lower() if country_name else ""
    iso = COUNTRY_ISO.get(key)
    if not iso:
        return "🏁"  # Return F1 Checkered flag as fallback

    # Shift alpha characters to Unicode regional indicators (A = 127397 + 65)
    OFFSET = 127397
    return "".join(chr(ord(c) + OFFSET) for c in iso.upper())


@bot.command()
async def raceweekend(ctx):
    """
    Displays the schedule for the upcoming F1 Grand Prix weekend with live countdowns.
    Usage: !raceweekend
    
    Note: Updates the sent message every minute in a loop until the weekend sessions end.
    """
    try:
        # Set local time zone for displaying session times (default: America/Port_of_Spain)
        tz_local = pytz.timezone("America/Port_of_Spain")
        
        # Load F1 schedule details
        schedule = fastf1.get_event_schedule(datetime.now().year, include_testing=True)

        # Locate the next chronological event schedule
        next_event = None
        for _, event in schedule.iterrows():
            first_session_time = None
            for i in range(1, 8):
                key = f"Session{i}DateUtc"
                if key in event and not pd.isna(event[key]):
                    first_session_time = event[key]
                    if first_session_time.tzinfo is None:
                        first_session_time = pytz.utc.localize(first_session_time)
                    break
            # Pick first event where the starting session resides in the future
            if first_session_time and first_session_time > datetime.now(pytz.utc):
                next_event = event
                break

        if next_event is None:
            await ctx.send("No upcoming races found for this season.")
            return

        # Fetch regional flag
        country_flag = country_to_emoji(next_event['Country'])

        # Check if this upcoming weekend has sprint format details
        is_sprint = False
        for key in ["SprintDateUtc", "Session3DateUtc", "Sprint Shootout"]:
            if key in next_event and not pd.isna(next_event[key]):
                is_sprint = True
                break

        # Map correct session types depending on Sprint vs Standard calendar rules
        if is_sprint:
            session_names = ["Practice 1", "Sprint Qualifying", "Sprint Race", "Qualifying", "Race"]
            session_keys = ["Session1DateUtc", "Session2DateUtc", "Session3DateUtc", "Session4DateUtc", "Session5DateUtc"]
        else:
            session_names = ["Practice 1", "Practice 2", "Practice 3", "Qualifying", "Race"]
            session_keys = ["Session1DateUtc", "Session2DateUtc", "Session3DateUtc", "Session4DateUtc", "Session5DateUtc"]

        # Build clean session details list
        session_list = []
        for name, key in zip(session_names, session_keys):
            if key in next_event and not pd.isna(next_event[key]):
                session_time = next_event[key]
                if session_time.tzinfo is None:
                    session_time = pytz.utc.localize(session_time)
                session_list.append((name, session_time))

        if not session_list:
            await ctx.send("No session data available for the next event.")
            return

        # Helper method to dynamically generate the live embed representation
        def build_embed(next_idx=None):
            embed = discord.Embed(
                title=f"{country_flag} {next_event['EventName']}",
                description=f"**Circuit:** {next_event['Location']}\n**Round:** {next_event['RoundNumber']}",
                color=discord.Color.red()
            )
            now = datetime.now(pytz.utc)

            # Compute countdown timers for all weekend sessions
            for idx, (session_name, session_time) in enumerate(session_list):
                diff = session_time - now
                days, remainder = divmod(max(diff.total_seconds(), 0), 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, _ = divmod(remainder, 60)
                countdown = f"{int(days)}d {int(hours)}h {int(minutes)}m" if diff.total_seconds() > 0 else "Ongoing or finished"

                # Localize and display datetime
                local_time = session_time.astimezone(tz_local)
                formatted_time = local_time.strftime("%A, %d %B %Y • %I:%M %p %Z")

                # Insert next up label if session matches index
                if next_idx == idx:
                    status = f"➡️ **NEXT UP**\nCountdown: {countdown}"
                else:
                    status = ""

                embed.add_field(
                    name=session_name,
                    value=f"{formatted_time}\n{status}",
                    inline=False
                )

            return embed

        # Determine index of the upcoming session
        next_session_index = None
        for idx, (_, time) in enumerate(session_list):
            if (time - datetime.now(pytz.utc)).total_seconds() > 0:
                next_session_index = idx
                break

        # Send initial embed info
        message = await ctx.send(embed=build_embed(next_session_index))

        # Enter refresh loop: update countdowns every 60s until all sessions conclude
        while next_session_index is not None:
            now = datetime.now(pytz.utc)
            _, session_time = session_list[next_session_index]
            diff = session_time - now
            # If current active session ends/begins, focus on next chronological slot
            if diff.total_seconds() <= 0:
                next_session_index += 1
                if next_session_index >= len(session_list):
                    next_session_index = None
            
            # Edit the message layout asynchronously
            await message.edit(embed=build_embed(next_session_index))
            # Wait for 60 seconds before next iteration
            await asyncio.sleep(60)

    except Exception as e:
        await ctx.send(f"Error fetching race data: {e}")


@bot.command(name="drivers", aliases=["drier"])
async def drivers(ctx):
    """
    Displays a list of driver names and their abbreviations for the current season.
    Usage: !drivers or !drier
    """
    try:
        # Load F1 drivers info synchronously
        def get_drivers():
            ergast = fastf1.ergast.Ergast()
            return ergast.get_driver_info(season='current')
            
        # Retrieve drivers info off-thread
        df = await asyncio.to_thread(get_drivers)
        
        if df.empty:
            await ctx.send("🏁 No driver data found for the current season.")
            return

        embed = discord.Embed(
            title="F1 Driver Abbreviations",
            description="Use these 3-letter codes for commands like `!compare`.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Sort values alphabetically by familyName
        df = df.sort_values('familyName')
        
        # Build driver abbreviations print block
        description = ""
        for i, row in df.iterrows():
            code = row['driverCode']
            name = f"{row['givenName']} {row['familyName']}"
            if pd.isna(code):
                continue
            description += f"**{code}**: {name}\n"

        embed.description = f"Use these 3-letter codes for commands like `!compare`.\n\n{description}"
        embed.set_footer(text="Data provided by FastF1")
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error fetching driver list: {e}")


@bot.command()
async def download(ctx):
    """
    Provides the MEGA download link for the app.
    Usage: !download
    """
    embed = discord.Embed(
        title="Download My App",
        description="You can download the app from the link below:\n\n[Download Here](https://mega.nz/file/umx3WaAK#nfx0keKq9B66FEpawp3Aic_kYnAFEXCJ9drdV9QlcMc)",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="Thank you for downloading!")
    await ctx.send(embed=embed)


@bot.command()
# Limit execution specifically to users with the Gamer role
@commands.has_role(secret_role)
async def secret(ctx):
    """
    A secret command accessible only to users with the 'Gamer' role.
    Usage: !secret
    """
    await ctx.send("Welcome to the club!")


@secret.error
async def secret_error(ctx, error):
    """
    Catches MissingRole exceptions and alerts users who lack authorization.
    """
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do not have permission to do that!")


# ==============================================================================
#                               BOT INITIALIZATION
# ==============================================================================

# ==============================================================================
#                               HEALTH CHECK SERVER
# ==============================================================================

def run_health_check_server():
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    
    port = int(os.environ.get("PORT", 8080))
    
    class HealthCheckHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()
                
        def log_message(self, format, *args):
            # Suppress logging to stdout to avoid clutter
            pass

    server = HTTPServer(("", port), HealthCheckHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

# Start the health check server
run_health_check_server()


# Start the bot. Logs are channeled through the FileHandler at DEBUG severity level.
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
