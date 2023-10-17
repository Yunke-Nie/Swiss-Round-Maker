# Swiss Round Maker

> Auther: Yunke Nie

## Description

This is a Discord Bot that provides Swiss-round tournament service, with a konami-like tiebreaker.

## Instruction

After inviting the bot to your server via Discord bot console to your server, you will have a token to replace the token in bot.py.

You may also need to change the fields of roles in bot.py to fit your server.

Run python bot.py

## Command

!announce: to announce the incoming tournament, will notice tournament players to join

!start: to start and initialize the tournament

!pair: Make pairing for each round

Under each round, there will be 3 reaction buttons under the message, For example:

Room 1: Player A vs. Player B

The reaction button 'L' stands left player - player A won the game.
The reaction button 'D' stands for draw of the game.
The reaction button 'R' stands right player - player B won the game.