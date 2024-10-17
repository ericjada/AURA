
# Discord Bot Project with Ollama (llama3.2)

## Description

Aura is a Discord bot built using the `discord.py` library and powered by the Ollama large language model. Aura offers a suite of features designed to enhance user interaction and provide entertainment within a Discord server. It leverages SQLite for persistent storage of user data, including birthdays, conversation history, and command logs. The bot is designed to be modular, with each feature set implemented as a separate "cog" for easy maintenance and expansion. 

# AURA Features

AURA provides a variety of features categorized into the following sections:

## Chat and AI Interaction:
- **Chat with LLaMA**: Use the `/chat` command to converse with the LLaMA language model.
- **System Prompt Setting**: Customize the initial system prompt using the `/set_prompt` command.
- **Conversation Memory Management**: Reset your conversation history with `/reset_memory`.

## Server Information and User Profiles:
- **Server Insights**: Use `/serverinfo` to get detailed server information such as server ID, member count, and creation date.
- **User Profiles**: View comprehensive user profiles using `/whois`, displaying details like user ID, status, and join date.

## Games and Entertainment:
- **Rock-Paper-Scissors**: Play Rock-Paper-Scissors with AURAcoin bets.
  - `/rps_challenge @[user] [amount]`: Challenge a user.
  - `/rps_accept`: Accept a challenge.
  - `/rps_decline`: Decline a challenge.
  - `/rps_choice [choice]`: Make your choice of rock, paper, or scissors.
  - `/rps_rules`: View the rules.

- **Dice Rolling**: Roll virtual dice with `/roll` using formats like `NdN` and `NdN+M`.
- **Coin Flip**: Flip a virtual coin using `/coinflip`.
- **Dice Duels**: Bet AURAcoin in dice duels.
  - `/dice_duel_challenge @[user] [amount] [dice]`: Challenge a user.
  - `/dice_duel_accept`: Accept a duel.
  - `/dice_duel_decline`: Decline a duel.
  - `/dice_duel_cancel`: Cancel your challenge.

- **Duels**: Challenge users to duels.
  - `/duel_challenge @[user] [amount]`: Start a duel.
  - `/duel_accept`: Accept a duel.
  - `/duel_decline`: Decline a duel.
  - `/duel_attack`: Attack during your turn.
  - `/duel_leaderboard`: View the duel leaderboard.
  - `/duel_rules`: View the rules.

## Birthdays:
- **Birthday Management**: Set your birthday with `/set_birthday [date]` (format: YYYY-MM-DD).
- **Birthday Countdown**: Check the countdown to a user's birthday using `/birthday_countdown`, optionally mentioning another user with `@[user]`.
- **Birthday Wishes**: AURA automatically sends birthday wishes on users' birthdays.

## AURAcoin:
- **AURAcoin**: Virtual currency used in various games within AURA.

## Other Games (Under Development):
- Blackjack
- Fishing
- LLM Trivia
- Lottery
- Roulette
- Slots


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
## Modular Structure with Cogs

AURA is designed with a modular structure using cogs. Here’s a list of the cogs included:

- **birthday.py**: Manages user birthdays, sending birthday wishes and countdowns.
- **chat.py**: Enables chat with the Ollama LLM, including prompt setting and memory management.
- **coinflip.py**: Provides a coin flip command.
- **dice.py**: Handles dice rolling with custom modifiers.
- **dice_duel.py**: Facilitates dice duels with AURAcoin betting.
- **duel_arena.py**: Manages user duels with AURAcoin bets.
- **general.py**: Includes basic commands like ping.
- **info.py**: Displays server and user information.
- **llm_trivia.py**: Offers an LLM-powered trivia game.
- **lottery.py**: Manages a lottery system.
- **RockPaperScissors.py**: Allows Rock-Paper-Scissors games with AURAcoin.
- **roulette.py**: Provides a roulette game.
- **slots.py**: Offers a slot machine game.

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
