## Idol Gacha Commands
- **!gacha | !g**: Rolls a random idol card that you can catch with a Pokeball
  - Idols can only be caught by the user who rolled them
  - **!gacha [x] | !g**: Admin only. Rolls the idol whose Idol ID matches [x]
- **!release [x] | !r**: Releases the idol named [x] from player's party
  - Spelling and Capitalization must match database
- **!profile | !p**: Displays player's profile with their earned titles and current party members
- **!resetgacha | !rg**: Admin only. Releases all caught idols back into the wild
- **!addtitle "[x]" | !newtitle "[x]"**: Admin only. Adds a new title named [x] to the database
  - Optional 2nd argument for the new title's ID
- **!addgroup "[x]" "[x.jpg]" (a) (g) | !newgroup | !addg | !newg**: Admin only. Adds a new group named [x] to the database with the logo file [x.jpg]
  - Optional 3rd argument for the new group's associated title_id
  - Optional 4th argument for the new group's ID
- **!addidol "[x]" "[x.jpg]" (g) (i) | !newidol | !addi | !newi**: Admin only. Adds a new idol named [x] to the database with the image file [x.jpg]
  - Optional 3rd argument for the new idol's group ID [g] (leave blank for Soloist)
  - Optional 4th argument for the new idol's ID [i]
- **!resetrolls [x] | !rr [x]**: Admin only. Resets the user [x]'s rolls to max
  - [x] can be an @ of the user or the user's ID
- **!setrolls [x] [i] | !sr [x] [i]**: Admin only. Sets the user [x]'s rolls to [i]
  - [x] can be an @ of the user or the user's ID
  - [i] must be at least 0
- **!addroll [x] (i) | !ar [x] (i)**: Admin only. Increases the user [x]'s rolls by [i] (default is +1)
  - [x] can be an @ of the user or the user's ID
  - [i] must be greater than 0


## Other Commands/Features (in order they were added)

- **!hello | !hi | /hello**: Bot says hello back
- **!goodmorning | !gm | !morning**: Bot says good morning back
- **!sendembed**: Displays an embed
  - Currently just a formatting template
- **!ping | !p**: Displays user's current ping
- **!meme | !memes | !m**: Displays a random trending meme from Reddit
- **!cat | !cats | !catpic | !catt | !c**: Displays a random trending cat pic from Reddit
- On member join: Welcomes new member with a random idol's picture and member count
- **!level | !l | /level** : Displays user's level statistics (current level, current XP, and total XP required to reach next level)
  - Every message sent in the discord gives a random amount of XP ranging from 1-25, including this command
  - The level statistics displayed do not include the XP gained from sending this command
  - The amount of XP required to level up increases exponentially with each level
- **!inspire | !inspiration | !i | !quote**: Sends a random inspirational quote
- **!balance | !b**: Displays user's Wallet Balance and Bank Balance (creates new bank account if the user does not have one)
- **!beg**: A random amount of coins ranging from 1-100 is added to user's Wallet
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
8. Make sure Admin's User ID is saved in the repo's folder in a file called "admin.txt"
9. Install Python if necessary
10. Install Prettier if necessary (might already be in node_modules, need to check)
    - Open "Extensions" tab on the sidebar (symbol that looks like tetris squares)
    - Find and install "Prettier - Code formatter"
    - `CTRL`+`,` to open Settings on Windows or Linux
    - Search for "Editor: Default Formatter" and select "Prettier - Code formatter" from the dropdown
    - Search for "Editor: Format On Save" and turn on
    - To apply Prettier to current file, Save
      - Or `CTRL`+`Shift`+`P` to open the command palette on Windows, then select "Format Document"
11. In the terminal, run `install discord`, `pip install easy-pil`, and `pip install asyncpraw` if necessary (add ` --user` at the end if you run into any permissions issues)
    - If asyncpraw is outdated, run `pip install --upgrade https://github.com/praw-dev/asyncpraw/archive/master.zip` to update to latest version
   


## Steps to Push New Changes to Current Branch
1. `git pull` to make sure local repo is up-to-date with GitHub
   - Can also use `git fetch` to check for updates from GitHub without pulling yet
   - May need to `git add *` and `git stash` local changes to update with `git pull`, then `git stash pop` to reapply local changes
     - Can also `git stash apply` to keep stashed files in the stack, then `git stash drop` when no longer needed
2. `git add *` to add all files to the commit
   - Any files that should be ignored need to be added to the .gitignore file
3. `git commit m ""` and write commit message inside quotations
4. `git push` to push commit to GitHub
   - If working on a new branch, use `git push origin [new-branch-name]`


## Steps to Create a New Feature Branch
1. `git stash` any changes
2. `git checkout -b [new-branch-name] [old-branch-name]` to create and move to the new branch
   - The new branch becomes a child of the old branch
   - Can leave out `checkout` to create the new branch but stay on the old branch
3. Can `git stash pop` to reapply changes to the new branch