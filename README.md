
# Discord Bot Project with Ollama (llama3.2)

## Description

Aura is a Discord bot built using the `discord.py` library and powered by the Ollama large language model. Aura offers a suite of features designed to enhance user interaction and provide entertainment within a Discord server. It leverages SQLite for persistent storage of user data, including birthdays, conversation history, and command logs. The bot is designed to be modular, with each feature set implemented as a separate "cog" for easy maintenance and expansion. 

## Features
Aura provides a variety of features, categorized into the following sections:
Chat and AI Interaction:
●
Chat with LLaMA: Users can have conversations with the LLaMA language model using the /chat command.
●
System Prompt Setting: Users can customize the initial system prompt for their chat sessions using the /set_prompt command.
●
Conversation Memory Management: Users can reset their conversation history using the /reset_memory command.
Server Information and User Profiles:
●
Server Insights: Obtain detailed information about the server using the /serverinfo command. This includes server ID, member count, and creation date.
●
User Profiles: View comprehensive user profiles with the /whois command, displaying user ID, status, and join date.
Games and Entertainment:
●
Rock-Paper-Scissors: Compete against other users in Rock-Paper-Scissors using AURAcoin as bets.
○
Use /rps_challenge @[user] [amount] to challenge a user.
○
Use /rps_accept to accept a challenge.
○
Use /rps_decline to decline a challenge.
○
Use /rps_choice [choice] to choose rock, paper, or scissors in an active game.
○
Use /rps_rules to view the rules.
●
Dice Rolling: Roll virtual dice with custom modifiers using the /roll command, supporting formats like "NdN" and "NdN+M". The command includes input validation to prevent invalid rolls and limits the number of dice for practicality.
●
Coin Flip: Make quick decisions or have some fun with the /coinflip command.
●
Dice Duels: Engage in dice duels with other players using AURAcoin as bets.
○
Use /dice_duel_challenge @[user] [amount] [dice] to challenge a user.
○
Use /dice_duel_accept to accept a challenge.
○
Use /dice_duel_decline to decline a challenge.
○
Use /dice_duel_cancel to cancel a challenge you sent.
●
Duels:
○
Use /duel_challenge @[user] [amount] to challenge a user.
○
Use /duel_accept to accept a challenge.
○
Use /duel_decline to decline a challenge.
○
Use /duel_attack to attack during your turn.
○
Use /duel_leaderboard to view the leaderboard.
○
Use /duel_rules to view the rules.
Birthdays:
●
Birthday Management: Users can set their birthdays using the /set_birthday [date] command, where [date] is in YYYY-MM-DD format.
●
Birthday Countdown: Check the countdown to a user's birthday using the /birthday_countdown command, optionally specifying a user with @[user].
●
Birthday Wishes: The bot automatically sends birthday wishes to users on their birthdays.
AURAcoin:
●
AURAcoin is the virtual currency used within Aura.
Other Games (Under Development):
●
Blackjack
●
Fishing
●
LLM Trivia
●
Lottery
●
Roulette
●
Slots

## Installation and Setup

1.  **Install Python:** Ensure you have Python 3.7 or later installed on your system.
2.  **Install Required Libraries:** Install the necessary Python libraries using pip:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up Ollama:**
    *   Download and install Ollama from [https://ollama.ai/](https://ollama.ai/)
    *   Start the Ollama server by running `ollama serve` in your terminal.
4.  **Discord Bot Token:**
    *   Create a Discord bot account and obtain a bot token.
    *   Create a file named `token.env` in the root directory of the project and add the following line, replacing `YOUR_DISCORD_TOKEN` with your actual token:
        ```
        DISCORD_TOKEN=YOUR_DISCORD_TOKEN
        ```
5.  **Database Setup:**
    *   Create a SQLite database file named `aura_memory.db` in the `group_memories` folder.
    *   Ensure the database file path is correctly specified in the bot's code.
6.  **Run the Bot:** Execute the `bot.py` file to start the Discord bot.

## Usage

Once the bot is running and connected to your Discord server, you can use the slash commands provided by each cog. Type `/` in a Discord channel to see a list of available commands.

## Cogs
Aura is designed with a modular structure using cogs. Here's a list of the cogs included:
●
birthday.py: Manages user birthdays, sending birthday wishes and providing countdown functionality.
●
chat.py: Enables chatting with the Ollama LLM, including prompt setting and memory management.
●
coinflip.py: Provides a coin flip command.
●
dice.py: Enables dice rolling with custom modifiers.
●
dice_duel.py: Facilitates dice duels with AURAcoin betting.
●
duel_arena.py: Manages duels between users with AURAcoin bets.
●
general.py: Includes basic commands like ping.
●
info.py: Provides commands to display server information and user details.
●
llm_trivia.py: Provides a trivia game powered by an LLM.
●
lottery.py: Manages a lottery system.
●
RockPaperScissors.py: Allows users to play Rock-Paper-Scissors against each other using AURAcoin.
●
roulette.py: Offers a roulette game.
●
slots.py: Provides a slot machine game.

## Logging

Aura logs various events to the SQLite database for analysis and debugging. This includes:

*   **Command Usage:** Logs each command executed, the user who invoked it, and the input and output data.
*   **Dice Roll Memory:** Saves the input and output of the `/roll` command for potential future reference or analysis.

## Contributing

Contributions to the Aura project are welcome! If you have any ideas, bug fixes, or new features you'd like to add, feel free to submit a pull request.

## Disclaimer

This project is a continuous work in progress. Features, functionality, and documentation may change as the development evolves. While the bot is fully operational, there may be ongoing updates, improvements, and bug fixes. Please check back regularly for the latest updates, and feel free to contribute or report issues. Your feedback and participation are highly appreciated!

# Support My Projects

If you enjoy my work and would like to support my projects, consider making a donation. Your contributions help me continue developing new projects. Every little bit helps!

<p align="center">
    <a href="https://www.paypal.com/donate/?hosted_button_id=NSFMYDYRMWMDY">
        <img src="./group_memories/AURA_Images/paypal.png" alt="Donate via PayPal" />
    </a>
    <br />
    <a href="https://www.paypal.com/donate/?hosted_button_id=NSFMYDYRMWMDY">Donate via PayPal</a>
    <br />
</p>
<br>
<p align="center">
    <img src="./group_memories/AURA_Images/btc-address.png" alt="Donate BTC via QR code" />
    <br />
    <a href="bitcoin:bc1qwky9tu333yszy0jxep93aqnfuh3qw5uykwrk3x">Donate BTC</a>
    <br />
</p>
<br>
<p align="center">
    <img src="./group_memories/AURA_Images/eth-address.png" alt="Donate ETH via QR code" />
    <br />
    <a href="ethereum:0xb9A5b1B571D760fb508cF0D12ccDDcCC6b232dBe">Donate ETH</a>
    <br />
</p>
<br>
<p align="center">
    <img src="./group_memories/AURA_Images/doge-address.png" alt="Donate DOGE via QR code" />
    <br />
    <a href="bitcoin:DTNdC9zrv3aHZB64ukMZZw3Nt8RQ2NoUeU">Donate DOGE</a>
    <br />
</p>
<br>
<p align="center">
    <img src="./group_memories/AURA_Images/xrp-address.png" alt="Donate XRP via QR code" />
    <br />
    <a href="ripple:rHzob7LN3usgbEYzREiNRHZUgeFvHK1dhr">Donate XRP</a>
    <br />
</p>
<br>
Thank you for your support!

## Collaboration and AI Integration

Throughout the development of this Discord bot project, I utilized the assistance of ChatGPT to brainstorm and refine key features like the AURA assistant and mini-games integration. With the help of ChatGPT's insights, I was able to enhance the bot's interaction logic and create a more user-friendly experience.

## Additional Resources

- [Ollama API Documentation](https://ollama.com)
- [Built with Llama](https://llama3.org)
- [LLaVA](https://github.com/haotian-liu/LLaVA/tree/main)

## 3P Licenses

This project integrates third-party APIs and models which are licensed under their respective terms. You can find the licenses for these integrations here:

- [Ollama API License](https://github.com/ollama/ollama/blob/main/LICENSE)
- [Llama3.2 License](https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE)
- [LLaVA License](https://github.com/haotian-liu/LLaVA/blob/main/LICENSE)

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
