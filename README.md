## Commands/Features (in order they were added)

- **!hello / !hi**: Bot says hello back
- **!goodmorning / !gm / !morning**: Bot says good morning back
- **!sendembed**: Displays an embed
  - Currently just a formatting template
- **!ping / !p**: Displays user's current ping
- **!meme / !memes / !m**: Displays a random trending meme from Reddit
- **!cat / !cats / !catpic / !catt / !c**: Displays a random trending cat pic from Reddit
- On member join: Welcomes new member with a random idol's picture and member count
- **!level / !l**: Displays user's level statistics (current level, current XP, and total XP required to reach next level)
  - Every message sent in the discord gives a random amount of XP ranging from 1-25, including this command
  - The level statistics displayed do not include the XP gained from sending this command
  - The amount of XP required to level up increases exponentially with each level


## How to Setup (in VS Code)

1. In VS Code, go to "Source Control" on the sidebar (symbol that looks like git branches)
2. Install Git if necessary
3. Click "Clone Repository"
4. Paste this repository's URL into the dropdown menu that appears at the top and click "Clone from GitHub" (will need to login to GitHub account)
5. Choose the folder the save the repo in
6. Click "Open" and "Yes, I trust the authors" if necessary
7. Make sure Bot's token is saved in the repo's folder in a file called "token.txt"
8. Install Python if necessary
9. In the terminal, run "install discord", "pip install easy-pil", and "pip install asyncpraw" if necessary (add " --user" at the end if you run into any permissions issues)
