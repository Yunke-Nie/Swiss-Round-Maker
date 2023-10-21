import discord
from discord.ext import commands
import random
import asyncio
import pandas as pd
import re
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.reactions = True  # Enable reaction events
intents.members = True    # Enable member-related events if needed
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Global Variables
pairings = {}
scores = {}  # e.g., {player: [3, 1, 0, 3], ...} for each round
byes = set()  # Players who got a bye
current_round = 0
MAX_ROUNDS = 4  # Constant

player_data = pd.DataFrame(columns=['Player Name', 'Score', 'Number of Wins', 'Number of Draws', 'Number of Losses', 'Tiebreaker', 'Opponents',
                                    'WinRate'])

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.command(name='start')
@commands.has_role('tournament organizer')
async def start_tournament(ctx):
    # Reset Global Variables
    global pairings, scores, byes, current_round, player_data, MAX_ROUNDS
    
    pairings = {}
    scores = {}
    byes = set()
    current_round = 0
    MAX_ROUNDS = 4  # Reset to default value
    player_data = pd.DataFrame(columns=['Player Name', 'Score', 'Number of Wins', 'Number of Draws', 'Number of Losses', 'Tiebreaker', 'Opponents', 'WinRate'])

    role = discord.utils.get(ctx.guild.roles, name="tournament duelist")
    duelists = [member for member in ctx.guild.members if role in member.roles]
    
    num_duelists = len(duelists)

    if num_duelists < 4:
        await ctx.send("目前已有" + str(num_duelists)  + "报名，群赛将准时开始")
        return

    if num_duelists <= 8:
        MAX_ROUNDS = 3
    
    # Initialize player data in the DataFrame
    for member in duelists:
        player_data = player_data.append({'Player Name': member.name,
                                          'Score': 0,
                                          'Number of Wins': 0,
                                          'Number of Draws': 0,
                                          'Number of Losses': 0,
                                          'Tiebreaker': 0,
                                          'Opponents': [],
                                          'WinRate': 0}, ignore_index=True)

    await ctx.send("Tournament has started!")

@bot.command(name='announce')
@commands.has_role('tournament organizer')
async def announce(ctx):
    role = discord.utils.get(ctx.guild.roles, name="tournament duelist")
    duelists = [member for member in ctx.guild.members if role in member.roles]
    num_duelists = len(duelists)
    if num_duelists < 4:
        await ctx.send("目前已有" + str(num_duelists) + "报名， 不足4人群赛无法开始")
        return
    else:
        await ctx.send("目前已有" + str(num_duelists)  + "报名，群赛将准时开始")

@bot.command(name='pair')
@commands.has_role('tournament organizer')
async def pair(ctx):
    global player_data
    num_players = len(player_data)
    global current_round
    current_round += 1

    match_pairings = []

    if current_round == 1:
        await ctx.send("Round 1:")
        shuffled_player_data = player_data.sample(frac=1).reset_index(drop=True)
    else:
        await ctx.send(f'Round {current_round}:')
        update_player_data()
        shuffled_player_data = player_data.sort_values(by=['Score', 'Tiebreaker'], ascending=[False, True]).reset_index(drop=True)
    
    if num_players % 2 == 1:
        bye_player = shuffled_player_data.iloc[-1]
        shuffled_player_data = shuffled_player_data.iloc[:-1]
        bye_player_name = bye_player['Player Name']
        match_pairings.append((bye_player_name, 'bye'))
    
    used_players = set()
    for i, player_row in shuffled_player_data.iterrows():
        if player_row['Player Name'] not in used_players:
            for j, opponent_row in shuffled_player_data.iterrows():
                # Check if they haven't played against each other before and not the same player
                if opponent_row['Player Name'] not in used_players and opponent_row['Player Name'] != player_row['Player Name'] and opponent_row['Player Name'] not in player_row['Opponents']:
                    match_pairings.append((player_row['Player Name'], opponent_row['Player Name']))
                    used_players.add(player_row['Player Name'])
                    used_players.add(opponent_row['Player Name'])
                    break

    counter = 1
    for match in match_pairings:
        member1 = discord.utils.get(ctx.guild.members, name=match[0])
        member2 = discord.utils.get(ctx.guild.members, name=match[1]) if match[1] != 'bye' else None

        if member1 is None or (match[1] != 'bye' and member2 is None):
            await ctx.send("One or both of the mentioned users were not found.")
            return

        if match[1] != 'bye':
            match_message = await ctx.send(f'Room {counter}: {member1.mention} vs {member2.mention}')
            print(f'Room {counter}: {member1.mention} vs {member2.mention}')
            await match_message.add_reaction('🇱')  # L for player A win
            await match_message.add_reaction('🇩')  # D for players drew
            await match_message.add_reaction('🇷')  # R for player B win
        else:
            await ctx.send(f'{member1.mention} has a bye this round.')
            print(f'{member1.mention} has a bye this round.')
            player_data.loc[player_data['Player Name'] == member1.name, 'Number of Wins'] += 1

        counter += 1

    

@bot.event
async def on_reaction_add(reaction, user):
    # Check if the reaction is added by a user and not the bot itself
    if user.bot:
        return
    
    # Check if the reaction is added to a message with specific criteria (e.g., room announcement)
    # You can customize this logic based on your needs
    if reaction.message.content.startswith('Room'):
        # Assuming you have a way to extract the relevant match information from the message content
        # For example, you can parse the message to get the player names and room number
        # Example: "Room 1: @Player1 vs @Player2" => room_number, player1, player2
        # You should replace this parsing logic with your own
        match_info = parse_match_info(reaction.message.content)
        
        if match_info:
            room_number, player1, player2 = match_info

            # Assuming you have a way to determine the result based on the reaction emoji
            # For example, if 🇱 is for player A win, 🇷 is for player B win, and 🇩 is for draw
            # You should replace this logic with your own
            result = determine_result(player1, player2, reaction.emoji)

            if result:
                # Update the player_data DataFrame based on the result
                await update_result(player1, player2, reaction.emoji)
                user1 = await bot.fetch_user(player1)
                user2 = await bot.fetch_user(player2)

# Example function to parse match information from message content
def parse_match_info(message_content):
    # Search for the room number pattern
    room_match = re.search(r'Room (\d+):', message_content)
    
    # Search for player mentions and extract their names
    player_mentions = re.findall(r'<@!?(\d+)>', message_content)
    
    # If we have a room number and two player mentions, extract the names
    if room_match and len(player_mentions) == 2:
        room_number = room_match.group(1)
        
        # Extract player names using Discord.py (assuming you have a context or the bot instance)
        # If you don't have the bot instance or context, you can just use the user IDs (player_mentions) as placeholders
        player1 = player_mentions[0]  # Use bot.fetch_user(player_mentions[0]).name if you have bot or context
        player2 = player_mentions[1]  # Use bot.fetch_user(player_mentions[1]).name if you have bot or context
        
        return room_number, player1, player2

    return None

# Example function to determine the result based on the reaction emoji
def determine_result(player_1, player_2, emoji):
    # Implement your logic here to determine the result based on the emoji
    # For example, if 🇱 is for player A win, 🇷 is for player B win, and 🇩 is for draw
    # Replace this example with your actual result determination logic
    if emoji == '🇱':
        return player_1 + ' win'
    elif emoji == '🇷':
        return player_2 + ' win'
    elif emoji == '🇩':
        return 'Draw'
    return None

# Example function to update player_data DataFrame
async def update_result(player1, player2, result):
    global player_data  # Assuming player_data is a global variable
    user1 = await bot.fetch_user(player1)
    user2 = await bot.fetch_user(player2)
    # Find the row index for player1 and append player2 to their Opponents list
    player1_index = player_data[player_data['Player Name'] == user1.name].index[0]
    player_data.at[player1_index, 'Opponents'].append(user2.name)

    # Find the row index for player2 and append player1 to their Opponents list
    player2_index = player_data[player_data['Player Name'] == user2.name].index[0]
    player_data.at[player2_index, 'Opponents'].append(user1.name)
    # Update the 'Number of Wins', 'Number of Losses', and 'Number of Draws' based on the result
    if result == '🇱':
        player_data.loc[player_data['Player Name'] == user1.name, 'Number of Wins'] += 1
        player_data.loc[player_data['Player Name'] == user2.name, 'Number of Losses'] += 1
    elif result == '🇷':
        player_data.loc[player_data['Player Name'] == user2.name, 'Number of Wins'] += 1
        player_data.loc[player_data['Player Name'] == user1.name, 'Number of Losses'] += 1
    elif result == '🇩':
        player_data.loc[player_data['Player Name'] == user1.name, 'Number of Draws'] += 1
        player_data.loc[player_data['Player Name'] == user2.name, 'Number of Draws'] += 1


def update_player_data():
    global player_data
    # Calculate and update 'WinRate' and 'Tiebreaker' for all players
    for player in player_data['Player Name']:
        player_row = player_data[player_data['Player Name'] == player].iloc[0]
        player_wins = player_row['Number of Wins']
        player_draws = player_row['Number of Draws']
        player_opponents = player_row['Opponents']

        opponent_win_rates = []

        for opponent in player_opponents:
            opponent_row = player_data[player_data['Player Name'] == opponent].iloc[0]
            opponent_wins = opponent_row['Number of Wins']
            opponent_losses = opponent_row['Number of Losses']
            opponent_total_games = opponent_wins + opponent_losses
            opponent_win_rate = opponent_wins / opponent_total_games if opponent_total_games > 0 else 0
            opponent_win_rates.append(opponent_win_rate)

        # Calculate win rate and update the 'WinRate' column
        win_rate = player_wins / (player_wins + player_row['Number of Losses']) if (player_wins + player_row['Number of Losses']) > 0 else 0
        player_data.loc[player_data['Player Name'] == player, 'WinRate'] = win_rate

        # Calculate tiebreaker score and update the 'Tiebreaker' column
        tiebreaker = (3 * player_wins + player_draws) * 100000000

        if opponent_win_rates:
            avg_opponent_win_rate = sum(opponent_win_rates) / len(opponent_win_rates)
            tiebreaker += round(avg_opponent_win_rate * 10000000, 3)

        player_data.loc[player_data['Player Name'] == player, 'Tiebreaker'] = tiebreaker

        # Calculate and update 'Current Score' based on wins and draws
        current_score = 3 * player_wins + player_draws
        player_data.loc[player_data['Player Name'] == player, 'Score'] = current_score

@bot.command(name='standing')
@commands.has_any_role('tournament organizer', 'tournament duelist')
async def standings(ctx):
    global player_data
    update_player_data()
    # Sort the DataFrame by score and tiebreaker in descending order
    player_data = player_data.sort_values(by=['Score', 'Tiebreaker'], ascending=False)

    # Create a message with the standings
    standings_message = "Current Standings:\n"

    for rank, (index, row) in enumerate(player_data.iterrows(), start=1):
        player_name = row['Player Name']
        wins = row['Number of Wins']
        draws = row['Number of Draws']
        losses = row['Number of Losses']
        score = row['Score']
        tiebreaker = row['Tiebreaker']

        standings_message += f"**Rank {rank}:** {player_name}\n"
        standings_message += f"   Wins: {wins}, Draws: {draws}, Losses: {losses}\n"
        standings_message += f"   Score: {score}, Tiebreaker: {tiebreaker}\n\n"

    # Send the standings message to the Discord channel
    await ctx.send(standings_message)

@bot.command(name='add')
@commands.has_role('tournament organizer')
async def add_players(ctx):
    global player_data

    role = discord.utils.get(ctx.guild.roles, name="tournament duelist")
    duelists = [member for member in ctx.guild.members if role in member.roles]

    # Check if any new players need to be added
    new_players = [member for member in duelists if member.name not in player_data['Player Name'].tolist()]
    
    if not new_players:
        await ctx.send("No new players to add.")
        return

    # Add new players to the player_data DataFrame
    for member in new_players:
        player_data = player_data.append({'Player Name': member.name,
                                          'Score': 0,
                                          'Number of Wins': 0,
                                          'Number of Draws': 0,
                                          'Number of Losses': 0,
                                          'Tiebreaker': 0,
                                          'Opponents': [],
                                          'WinRate': 0}, ignore_index=True)

    await ctx.send(f"Added {len(new_players)} new players to the tournament.")

@bot.command(name='drop')
@commands.has_role('tournament organizer')
async def drop_players(ctx):
    global player_data

    role = discord.utils.get(ctx.guild.roles, name="tournament duelist")
    duelists = [member for member in ctx.guild.members if role in member.roles]

    # Check if any players need to be dropped
    players_to_drop = [player for player in player_data['Player Name'].tolist() if player not in [member.name for member in duelists]]
    
    if not players_to_drop:
        await ctx.send("No players to drop.")
        return

    # Exclude dropped players from future rounds
    global byes
    byes = byes.difference(set(players_to_drop))

    await ctx.send(f"Dropped {len(players_to_drop)} players from the tournament.")

# TODO: Timer    

# TODO: Rewind?

bot.run(TOKEN)
