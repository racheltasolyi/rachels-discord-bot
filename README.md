## Commands/Features (in order they were added)

- **!hello / !hi / /hello**: Bot says hello back
- **!goodmorning / !gm / !morning**: Bot says good morning back
- **!sendembed**: Displays an embed
  - Currently just a formatting template
- **!ping / !p**: Displays user's current ping
- **!meme / !memes / !m**: Displays a random trending meme from Reddit
- **!cat / !cats / !catpic / !catt / !c**: Displays a random trending cat pic from Reddit
- On member join: Welcomes new member with a random idol's picture and member count
- **!level / !l / /level** : Displays user's level statistics (current level, current XP, and total XP required to reach next level)
  - Every message sent in the discord gives a random amount of XP ranging from 1-25, including this command
  - The level statistics displayed do not include the XP gained from sending this command
  - The amount of XP required to level up increases exponentially with each level
- **!inspire / !inspiration / !i / !quote**: Sends a random inspirational quote
- **!balance / !b**: Displays user's Wallet Balance and Bank Balance (creates new bank account if the user does not have one)
- **!beg**: A random amount of coins ranging from 1-100 is added to user's Wallet
- **!gacha / !g**: Displays a random idol card that you can catch with a Pokeball
- **/uselessbuttonmenu**: Displays a button menu that sends a message whenever a button is pressed
- **!sync / !synccmd / !s**: Syncs and updates slash commands


## How to Setup (in VS Code)

1. In VS Code, go to "Source Control" on the sidebar (symbol that looks like git branches)
2. Install Git if necessary
3. Click "Clone Repository"
4. Paste this repository's URL into the dropdown menu that appears at the top and click "Clone from GitHub" (will need to login to GitHub account)
5. Choose the folder the save the repo in
6. Click "Open" and "Yes, I trust the authors" if necessary
7. Make sure Bot's token is saved in the repo's folder in a file called "token.txt"
8. Install Python if necessary
9. Install Prettier if necessary (might already be in node_modules, need to check)
  a. Open "Extensions" tab on the sidebar (symbol that looks like tetris squares)
  b. Find and install "Prettier - Code formatter"
  c. `CTRL`+`,` to open Settings on Windows or Linux
  d. Search for "Editor: Default Formatter" and select "Prettier - Code formatter" from the dropdown
  e. Search for "Editor: Format On Save" and turn on
  f. To apply Prettier to current file, Save
    i. Or `CTRL`+`Shift`+`P` to open the command palette on Windows, then select "Format Document"
10. In the terminal, run `install discord`, `pip install easy-pil`, and `pip install asyncpraw` if necessary (add ` --user` at the end if you run into any permissions issues)


## Steps to Push New Changes to Current Branch
1. `git pull` to make sure local repo is up-to-date with GitHub
  a. Can also use `git fetch` to check for updates from GitHub without pulling yet
  b. May need to `git add *` and `git stash` local changes to update with `git pull`, then `git stash pop` to reapply local changes
    i. Can also `git stash apply` to keep stashed files in the stack, then `git stash drop` when no longer needed
2. `git add *` to add all files to the commit
  a. Any files that should be ignored need to be added to the .gitignore file
3. `git commit m ""` and write commit message inside quotations
4. `git push` to push commit to GitHub