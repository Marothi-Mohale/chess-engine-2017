# Chess Engine (2017)

An upgraded Python chess engine based on an earlier chess project I originally wrote in 2017.

This repository reflects both the original idea and a more complete implementation of it. What started as an early experiment in chess logic has been upgraded into a playable terminal-based chess engine with legal move generation, board state handling, and a simple AI opponent.

## Overview

This project is a console-based chess engine written in Python. It supports standard chess movement rules, detects game-ending conditions, and allows a user to play by entering moves directly in the terminal.

It is designed to be readable, extendable, and useful as both a programming project and a demonstration of rule-based problem solving.

## Features

- Legal move generation
- Check, checkmate, and stalemate detection
- Castling
- En passant
- Pawn promotion
- FEN import and export
- Terminal-based gameplay
- UCI-style move input
- Simple minimax-based AI

## How the Game Is Played

This project is played entirely in the terminal or console.

When the program starts, it prints the board, shows whose turn it is, and waits for the player to enter a move.

Moves are entered using **UCI-style notation**, which means:

- the first two characters represent the starting square
- the next two characters represent the destination square

Example:

```text
e2e4
