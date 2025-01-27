# Discord Bot Project with Ollama (llama3.2)

## Description

Aura is a Discord bot built using the `discord.py` library and powered by the Ollama large language model. It offers a suite of features designed to enhance user interaction and provide entertainment within Discord servers. The bot leverages SQLite for persistent storage of user data and is built with a modular architecture using cogs.

## Key Features

- **AI Chat Integration**: Engage in conversations with LLaMA 3.2 through Ollama
- **User Management**: Track birthdays, user profiles, and server information
- **Gaming System**: Multiple games including:
  - Rock-Paper-Scissors with betting
  - Dice rolling and duels
  - Virtual currency (AURAcoin) system
  - More games in development (Blackjack, Fishing, etc.)

## Quick Start

1. **Prerequisites**
   ```bash
   # Install Python 3.7+
   # Install Ollama from https://ollama.ai/
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Start Ollama server
   ollama serve
   ```

2. **Configuration**
   ```bash
   # Create token.env file
   echo "DISCORD_TOKEN=YOUR_DISCORD_TOKEN" > token.env
   
   # Initialize database
   mkdir -p group_memories
   touch group_memories/aura_memory.db
   ```

3. **Launch**
   ```bash
   python bot.py
   ```

## Command Usage

Use slash commands in Discord to interact with AURA:

### Chat Commands
- `/chat` - Talk with LLaMA
- `/set_prompt` - Customize AI behavior
- `/reset_memory` - Clear chat history

### User Commands
- `/serverinfo` - View server details
- `/whois` - Check user profiles
- `/set_birthday` - Set your birthday

### Games
- `/rps_challenge @user amount` - Start Rock-Paper-Scissors
- `/roll NdN+M` - Roll dice (e.g., 2d6+3)
- `/duel_challenge @user amount` - Begin a duel

[Additional commands and documentation...]

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
