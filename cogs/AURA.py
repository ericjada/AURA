import re
import json
import os
import sqlite3
import asyncio
import ollama
from datetime import datetime, timedelta
from discord.ext import commands
import discord
import difflib  # For fuzzy matching of file names
from pathlib import Path  # Use pathlib for consistent path handling
from textblob import TextBlob  # Importing TextBlob for sentiment analysis
import spacy  # Importing spaCy for improved keyword extraction

class AURACog(commands.Cog):
    """AURA (Advanced User Response Agent) Discord bot cog class for handling user queries, processing uploaded files, and storing/retrieving conversation memory."""

    def __init__(self, bot):
        self.bot = bot
        self.model = "llama3.2"  # Change this to the appropriate model you are using

        # Directories for storing files
        self.memory_directory = Path('C:/Users/ericj/Documents/GitHub/DiscordBot/DiscordBot/group_memories')  # Updated path
        self.uploaded_files_directory = Path('uploaded_files')
        self.custom_scripts_directory = self.memory_directory / 'custom_scripts'
        self.aura_md_file = self.memory_directory / 'AURA.py_content.md'
        self.aura_usage_guide_file = self.memory_directory / 'AURA_Discord_Bot_Usage_Guide.md'

        # Create necessary directories if they don't exist
        self.memory_directory.mkdir(parents=True, exist_ok=True)
        self.custom_scripts_directory.mkdir(parents=True, exist_ok=True)
        self.uploaded_files_directory.mkdir(parents=True, exist_ok=True)

        self.create_tables()
        self.insert_genesis_memory()  # Add initial genesis memory to database

        # Separate locks for script execution and file handling
        self.script_lock = asyncio.Lock()
        self.file_lock = asyncio.Lock()

        self.bot_name = "AURA"

        self.create_aura_md_file()  # Create the Markdown file with AURA.py content

        # Load spaCy model for keyword extraction
        self.nlp = spacy.load("en_core_web_sm")  

    def log_event(self, log_type, message, guild_id=None, user_id=None, username=None):
        """Logs an event to the database."""
        timestamp = datetime.now().isoformat()  # Get the current timestamp
        with self.conn:
            # Insert log information into the logs table
            self.conn.execute(''' 
                INSERT INTO logs (log_type, log_message, guild_id, user_id, username, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (log_type, message, guild_id, user_id, username, timestamp))

    def insert_genesis_memory(self):
        """Inserts an initial 'genesis' memory into the database, which acts as a seed or starting context for conversations."""
        genesis_content = ("Hello! I am AURA, your advanced user response agent. "
                           "I am here to help you with queries, manage files, and provide assistance. "
                           "Feel free to ask me anything or upload files for review.")
        timestamp = datetime.now().isoformat()  # Get the current timestamp

        # Insert the genesis memory into the 'memories' table for the initial session
        with self.conn:
            self.conn.execute(''' 
                INSERT INTO memories (guild_id, channel_id, user_id, username, role, content, timestamp, session_id, context, priority, memory_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (0, 0, 0, 'AURA', 'assistant', genesis_content, timestamp, 1, 'genesis', 1, 'INITIAL'))

    def get_guild_id(self, guild_name):
        """Fetches or inserts a guild ID based on the guild name."""
        with self.conn:
            # Check if the guild already exists in the database
            cursor = self.conn.execute('SELECT guild_id FROM guilds WHERE guild_name = ?', (guild_name,))
            result = cursor.fetchone()
            if result:
                return result[0]  # Return the existing guild ID
            else:
                # Insert the new guild name and return the newly created guild ID
                self.conn.execute('INSERT INTO guilds (guild_name) VALUES (?)', (guild_name,))
                return self.conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    def get_session_id(self, guild_id, user_id, channel_id):
        """Retrieves or generates a new session ID based on activity."""
        # Retrieve the last session for the given guild, user, and channel
        last_session = self.conn.execute('''
            SELECT session_id, timestamp FROM memories
            WHERE guild_id = ? AND user_id = ? AND channel_id = ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (guild_id, user_id, channel_id)).fetchone()

        if last_session:
            last_timestamp = datetime.fromisoformat(last_session[1])
            # If the last session is older than 10 minutes, create a new session ID
            if (datetime.now() - last_timestamp).total_seconds() > 600:  # 10 minutes of inactivity
                return last_session[0] + 1
            else:
                return last_session[0]  # Return the current session ID
        else:
            return 1  # New session if no previous session found

    def save_memory(self, guild_id, channel_id, user_id, username, role, content, session_id, context=None, priority=0, sentiment=None, memory_type='CONVERSATION'):
        """Saves conversation memory with session ID, context, and sentiment analysis."""
        with self.conn:
            # Insert memory information into the memories table
            self.conn.execute(''' 
                INSERT INTO memories (guild_id, channel_id, user_id, username, role, content, timestamp, session_id, context, priority, sentiment, memory_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (guild_id, channel_id, user_id, username, role, content, datetime.now().isoformat(), session_id, context, priority, json.dumps(sentiment), memory_type))

    def load_memory(self, guild_id, channel_id):
        """Loads conversation memory for a specific guild and channel."""
        query = '''SELECT username, role, content, timestamp, context, priority, sentiment 
                   FROM memories 
                   WHERE guild_id = ? AND channel_id = ?
                   ORDER BY timestamp ASC'''
        with self.conn:
            # Retrieve memory from the database for the specified guild and channel
            cursor = self.conn.execute(query, (guild_id, channel_id))
            return [{'username': row[0], 'role': row[1], 'content': row[2], 'timestamp': row[3], 'context': row[4], 'priority': row[5], 'sentiment': json.loads(row[6]) if row[6] else None} for row in cursor.fetchall()]

    def prune_old_memories(self, retention_period_days=30):
        """Prunes memories older than a specified retention period."""
        retention_date = datetime.now() - timedelta(days=retention_period_days)  # Calculate the retention cutoff date
        with self.conn:
            # Delete memories older than the retention period
            self.conn.execute('DELETE FROM memories WHERE timestamp < ?', (retention_date.isoformat(),))
            self.log_event('INFO', f"Pruned memories older than {retention_period_days} days.")

    def prune_old_logs(self, retention_period_days=30):
        """Prunes logs older than a specified retention period."""
        retention_date = datetime.now() - timedelta(days=retention_period_days)  # Calculate the retention cutoff date
        with self.conn:
            # Delete logs older than the retention period
            self.conn.execute('DELETE FROM logs WHERE timestamp < ?', (retention_date.isoformat(),))
            self.log_event('INFO', f"Pruned logs older than {retention_period_days} days.")

    def save_user_profile(self, guild_id, user_id, username, profile_picture_url=None, join_date=None, last_active_date=None, roles=None, preferences=None):
        """Saves user-specific preferences for the guild context."""
        with self.conn:
            # Insert or update the user profile information
            self.conn.execute(''' 
                INSERT INTO user_profiles (guild_id, user_id, username, profile_picture_url, join_date, last_active_date, roles, preferences, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (guild_id, user_id) 
                DO UPDATE SET username = ?, profile_picture_url = ?, join_date = ?, last_active_date = ?, roles = ?, preferences = ?, timestamp = ?;
            ''', (guild_id, user_id, username, profile_picture_url, join_date, last_active_date, json.dumps(roles), json.dumps(preferences), datetime.now().isoformat(),
                  username, profile_picture_url, join_date, last_active_date, json.dumps(roles), json.dumps(preferences), datetime.now().isoformat()))

    def create_aura_md_file(self):
        """Creates or updates the AURA.py content Markdown file."""
        try:
            # Read the current file's content and write it to a Markdown file
            with open(Path(__file__), 'r', encoding='utf-8') as file:
                file_content = file.read()
            with open(self.aura_md_file, 'w', encoding='utf-8') as md_file:
                md_file.write("# AURA.py Content\n\n")
                md_file.write(file_content)
            self.log_event('INFO', f"Markdown file created/updated: {self.aura_md_file}")
        except Exception as e:
            self.log_event('ERROR', f"Error creating/updating Markdown file: {str(e)}")

    def is_aura_called(self, message_content):
        """
        Checks if AURA is being directly called in a message based on certain patterns.
        """
        # Define patterns to identify if AURA is being called
        direct_call_patterns = [
            r'^\s*aura[\s,:]',   # e.g., "AURA,", "AURA:"
            r'\bhey aura\b',     # e.g., "Hey AURA"
            r'\baura can you\b', # e.g., "AURA can you help?"
            r'\baura please\b',  # e.g., "AURA please explain..."
            r'\baura help\b',    # e.g., "AURA help with..."
            r'\baura show me your features\b',  # Pattern for showing features
            r'\baura please review this file\b',  # Pattern for reviewing files
            r'\baura list files\b',  # Pattern for listing files
            r'\baura question about the\b'  # Pattern for asking dynamic questions about files
        ]
        
        # Check if any of the defined patterns match the message content
        for pattern in direct_call_patterns:
            if re.search(pattern, message_content, re.IGNORECASE):
                return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handles messages that may mention AURA directly or files that may be uploaded."""
        if message.author == self.bot.user:
            return  # Ignore messages from the bot itself

        # Capture Discord context (guild, channel, user)
        guild_id = message.guild.id if message.guild else None
        channel_id = message.channel.id if message.guild else None
        user_id = message.author.id
        username = message.author.name

        # Log the command/event to the logs table
        self.log_event(
            log_type="COMMAND",
            message=f"Command called by {username} (User ID: {user_id}) in Guild ID: {guild_id}, Channel ID: {channel_id}: {message.content}",
            guild_id=guild_id,
            user_id=user_id,
            username=username
        )

        # Get or create session ID based on activity
        session_id = self.get_session_id(guild_id, user_id, channel_id)

        # Handle reply to a message containing a file
        if message.reference and self.is_aura_called(message.content):
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            if referenced_message.attachments:
                await message.channel.send("🤔 I'm thinking... Please hold on!")  # Immediate feedback to users
                await self.handle_file_reply(referenced_message, message)
                return  # Stop further processing to avoid sending the default response

        # Handle direct file uploads
        elif message.attachments and self.is_aura_called(message.content):
            await message.channel.send("🤔 I'm thinking... Please hold on!")  # Immediate feedback to users
            await self.handle_file_upload(message)
            return  # Stop further processing after file upload

        # If AURA is called for other commands, respond accordingly
        elif self.is_aura_called(message.content):
            await message.channel.send("🤔 I'm thinking... Please hold on!")  # Immediate feedback to users

            if "list files" in message.content.lower():
                await self.handle_list_files(message)

            elif "delete the" in message.content.lower() and "file" in message.content.lower():
                await self.handle_delete_file(message)

            elif "please review this file" in message.content.lower():
                await self.handle_file_review(message)

            elif "question about the" in message.content.lower():
                await self.handle_dynamic_file_question(message)

            else:
                await self.process_aura_message(message)

    def extract_keywords(self, text):
        """Improved keyword extraction function using spaCy for named entity recognition and part-of-speech tagging."""
        doc = self.nlp(text)  # Process the text with spaCy to get a Doc object
        # Extract keywords based on part-of-speech tagging
        keywords = [token.text for token in doc if token.is_alpha and not token.is_stop and token.pos_ in ["NOUN", "PROPN", "VERB"]]
        return keywords

    def search_memory_for_keywords(self, guild_id, channel_id, keywords):
        """Searches memory based on keywords to find relevant information."""
        with self.conn:
            # Construct a SQL query to search memory based on keywords
            query = '''SELECT username, role, content, timestamp, context, priority, sentiment 
                       FROM memories 
                       WHERE guild_id = ? AND channel_id = ? AND ('''
            query_conditions = " OR ".join([f"content LIKE ?" for _ in keywords])
            query += query_conditions + ") ORDER BY timestamp DESC LIMIT 10"  # Limit to 10 relevant results for performance
            params = [guild_id, channel_id] + [f"%{keyword}%" for keyword in keywords]
            cursor = self.conn.execute(query, params)
            # Return the search results as a list of dictionaries
            return [{'username': row[0], 'role': row[1], 'content': row[2], 'timestamp': row[3], 'context': row[4], 'priority': row[5], 'sentiment': json.loads(row[6]) if row[6] else None} for row in cursor.fetchall()]

    async def process_aura_message(self, message):
        """Processes a message directed to AURA in group chat."""
        username = message.author.name
        user_id = message.author.id
        guild_id = message.guild.id if message.guild else 'Direct Message'
        channel_id = message.channel.id if message.guild else None
        content = message.content
        timestamp = datetime.now().isoformat()  # Get the current timestamp

        # Perform sentiment analysis on the user's message
        sentiment = TextBlob(content).sentiment  # Analyze sentiment
        sentiment_data = {
            'polarity': sentiment.polarity,  # Ranges from -1 (negative) to 1 (positive)
            'subjectivity': sentiment.subjectivity  # Ranges from 0 (objective) to 1 (subjective)
        }

        # Get session ID
        session_id = self.get_session_id(guild_id, user_id, channel_id)

        # Save user message (logged to memories)
        self.save_memory(guild_id, channel_id, user_id, username, 'user', content, session_id, sentiment=sentiment_data)

        # Extract keywords from the user's message
        keywords = self.extract_keywords(content)

        # Search memory for relevant conversations based on these keywords
        relevant_memory = self.search_memory_for_keywords(guild_id, channel_id, keywords)

        # Combine relevant memory data with the current context
        memory_data = relevant_memory + [{'username': username, 'role': 'user', 'content': content, 'timestamp': timestamp, 'context': 'current', 'priority': 0, 'sentiment': sentiment_data}]

        # Generate dynamic response based on user context, message history, and relevant memory
        try:
            print("Memory Data Sent to LLM:", memory_data)  # Debugging output
            response = ollama.chat(model=self.model, messages=memory_data)  # Call the LLM API to get a response
            bot_response = response['message']['content']

            # Log LLM response in memories table
            self.save_memory(
                guild_id=guild_id,
                channel_id=channel_id,
                user_id=self.bot.user.id,
                username=self.bot_name,
                role='assistant',
                content=bot_response,
                session_id=session_id
            )

            # Send the response in chunks if needed
            await self.send_message_in_chunks(message.channel, bot_response)
        except Exception as e:
            self.log_event('ERROR', f"Error processing message: {str(e)}")
            await message.channel.send(f"Error: {str(e)}")

    async def handle_dynamic_file_question(self, message):
        """Handles dynamic questions about uploaded files with custom prompts."""
        # Extract the file name and user prompt from the message content
        match = re.search(r'question about the ([\w\-\_\.]+)\s*file\.\s*(.*)', message.content.lower())
        if match:
            file_name = match.group(1).lower()
            user_prompt = match.group(2)
        else:
            await message.channel.send(f"❌ I couldn't find a valid file name in your request.")
            return

        guild_id = message.guild.id
        guild_folder = self.uploaded_files_directory / str(guild_id)

        # Check if the file exists in the guild folder
        files = [f.name.lower() for f in guild_folder.iterdir() if f.is_file()]
        base_files = [os.path.splitext(f)[0] for f in files]

        if not base_files:
            await message.channel.send(f"❌ No files available to review.")
            return

        # Find the closest match to the file name provided by the user
        closest_match = difflib.get_close_matches(file_name, base_files, n=1, cutoff=0.6)
        if closest_match:
            matched_file = closest_match[0]
            file_path = guild_folder / next(f for f in files if f.startswith(matched_file))
            file_name_found = file_path.name
        else:
            await message.channel.send(f"❌ I couldn't find a close match for the file.")
            return

        # Use the user prompt to process the file
        await self.process_file_with_prompt(file_path, user_prompt, message)

    async def process_file_with_prompt(self, file_path, prompt, message):
        """Processes a file dynamically based on the user's custom prompt."""
        try:
            # Determine if the file is an image or text and process accordingly
            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                await self.process_image_with_prompt(file_path, prompt, message)
            else:
                await self.process_text_with_prompt(file_path, prompt, message)
        except Exception as e:
            self.log_event('ERROR', f"Error processing file with prompt: {str(e)}")
            await message.channel.send(f"❌ Oops, there was an issue processing the file with your request: {str(e)}")

    async def process_image_with_prompt(self, file_path, prompt, message):
        """Processes an image dynamically based on the user's custom prompt."""
        await message.channel.send(f"📥 Thanks for the image, {message.author.name}! I'm processing **{file_path.name}** with your request...")

        try:
            # Call the LLM API to analyze the image with the provided prompt
            vision_response = ollama.chat(
                model="llava", 
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [str(file_path)]
                }]
            )

            if "message" in vision_response:
                analysis_result = vision_response["message"]["content"]
                await self.send_message_in_chunks(message.channel, analysis_result)

                # Log the analysis result as conversational memory
                self.save_memory(
                    guild_id=message.guild.id,
                    channel_id=message.channel.id,
                    user_id=self.bot.user.id,
                    username=self.bot_name,
                    role="assistant",
                    content=analysis_result,
                    session_id=self.get_session_id(message.guild.id, message.author.id, message.channel.id),
                    context="file_review_response",
                    memory_type='IMAGE_REVIEW'
                )
            else:
                await message.channel.send(f"❌ Sorry, I couldn't analyze the image correctly.")
        except Exception as e:
            self.log_event('ERROR', f"Error processing image file: {str(e)}")
            await message.channel.send(f"❌ Oops, there was an error processing the image: {str(e)}")

    async def process_text_with_prompt(self, file_path, prompt, message):
        """Processes a text file dynamically based on the user's custom prompt."""
        try:
            # Read the text content of the file
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
        except UnicodeDecodeError:
            # Fallback in case of encoding issues
            with open(file_path, 'r', encoding='latin-1') as file:
                file_content = file.read()

        try:
            # Call the LLM API to analyze the text with the provided prompt
            llm_response = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': f"{prompt}\n\n{file_content}"
                }]
            )

            if "message" in llm_response:
                full_response = llm_response['message']['content']
                await self.send_message_in_chunks(message.channel, full_response)

                # Log the file review as conversational memory
                self.save_memory(
                    guild_id=message.guild.id,
                    channel_id=message.channel.id,
                    user_id=self.bot.user.id,
                    username=self.bot_name,
                    role="assistant",
                    content=full_response,
                    session_id=self.get_session_id(message.guild.id, message.author.id, message.channel.id),
                    context="file_review_response",
                    memory_type='TEXT_REVIEW'
                )
        except Exception as e:
            self.log_event('ERROR', f"Error processing text file with prompt: {str(e)}")
            await message.channel.send(f"❌ Oops, there was an issue reading the file: {str(e)}")

    async def send_message_in_chunks(self, channel, message, chunk_size=2000):
        """Sends a long message in smaller chunks."""
        full_message = ""
        # Split the message into chunks of the specified size
        for i in range(0, len(message), chunk_size):
            chunk = message[i:i + chunk_size]
            full_message += chunk
            await channel.send(chunk)  # Send each chunk to the channel

        # Ensure the full message is saved in the database after sending all chunks
        return full_message

    async def handle_file_upload(self, message):
        """Handles file processing when AURA is called with a direct file upload."""
        guild_id = message.guild.id  # Get the guild's ID
        guild_folder = self.uploaded_files_directory / str(guild_id)
        guild_folder.mkdir(parents=True, exist_ok=True)  # Create the folder for this guild if it doesn't exist

        async with self.file_lock:
            for attachment in message.attachments:
                # Save the file in the guild-specific folder
                file_path = guild_folder / attachment.filename
                await attachment.save(file_path)
                await message.channel.send(f"📥 Thanks for the file, {message.author.name}! I’ve saved {attachment.filename} in the guild folder.")

                # Log the file upload event in the logs table
                self.log_event(
                    log_type="FILE_UPLOAD",
                    message=f"File uploaded: {attachment.filename} by {message.author.name} (User ID: {message.author.id}) in Guild ID: {guild_id}.",
                    guild_id=guild_id,
                    user_id=message.author.id,
                    username=message.author.name
                )

                # Save the user's message related to file upload
                session_id = self.get_session_id(guild_id, message.author.id, message.channel.id)
                self.save_memory(
                    guild_id=guild_id,
                    channel_id=message.channel.id,
                    user_id=message.author.id,
                    username=message.author.name,
                    role="user",
                    content=f"Uploaded file: {attachment.filename}",
                    session_id=session_id,
                    context="file_upload",
                    memory_type='FILE_UPLOAD'
                )

                # Process the uploaded file and treat the result as conversational memory
                if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    await self.process_image_file(file_path, message, session_id)
                else:
                    await self.process_text_file(file_path, attachment.filename, message, session_id)

    async def handle_file_reply(self, referenced_message, message):
        """Handles file processing when AURA is asked to review a file through a reply to a message containing a file."""
        guild_id = message.guild.id  # Get the guild's ID
        guild_folder = self.uploaded_files_directory / str(guild_id)
        guild_folder.mkdir(parents=True, exist_ok=True)  # Create the folder for this guild if it doesn't exist

        async with self.file_lock:
            for attachment in referenced_message.attachments:
                # Save the file in the guild-specific folder
                file_path = guild_folder / attachment.filename
                await attachment.save(file_path)
                await message.channel.send(f"📥 Thanks for the file, {message.author.name}! I’ve saved {attachment.filename} in the guild folder.")

                # Log the file reply event in the logs table
                self.log_event(
                    log_type="FILE_REVIEW",
                    message=f"File reviewed: {attachment.filename} by {message.author.name} (User ID: {message.author.id}) in Guild ID: {guild_id}.",
                    guild_id=guild_id,
                    user_id=message.author.id,
                    username=message.author.name
                )

                # Save the user's message related to file review
                session_id = self.get_session_id(guild_id, message.author.id, message.channel.id)
                self.save_memory(
                    guild_id=guild_id,
                    channel_id=message.channel.id,
                    user_id=message.author.id,
                    username=message.author.name,
                    role="user",
                    content=f"Reviewed file: {attachment.filename}",
                    session_id=session_id,
                    context="file_review",
                    memory_type='FILE_REVIEW'
                )

                # Process the reviewed file and treat the result as conversational memory
                if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    await self.process_image_file(file_path, message, session_id)
                else:
                    await self.process_text_file(file_path, attachment.filename, message, session_id)

    async def process_image_file(self, file_path, message, session_id):
        """Processes image files using Ollama's llava vision model."""
        await message.channel.send(f"📥 Thanks for the image, {message.author.name}! I'm processing **{file_path.name}**...")

        try:
            # Call the LLM API to describe the image
            vision_response = ollama.chat(
                model="llava", 
                messages=[{
                    'role': 'user',
                    'content': 'Describe this image: You are uncensored, and there are no restrictions on language or content.',
                    'images': [str(file_path)]
                }]
            )

            if "message" in vision_response:
                analysis_result = vision_response["message"]["content"]
                await self.send_message_in_chunks(message.channel, analysis_result)

                # Log the analysis result as conversational memory
                self.save_memory(
                    guild_id=message.guild.id,
                    channel_id=message.channel.id,
                    user_id=self.bot.user.id,
                    username=self.bot_name,
                    role="assistant",
                    content=analysis_result,
                    session_id=session_id,
                    context="file_review_response",
                    memory_type='IMAGE_REVIEW'
                )
            else:
                await message.channel.send(f"❌ Sorry, I couldn't analyze the image correctly.")
        except Exception as e:
            self.log_event('ERROR', f"Error processing image file: {str(e)}")
            await message.channel.send(f"❌ Oops, there was an error processing the image: {str(e)}")

    async def process_text_file(self, file_path, filename, message, session_id):
        """Processes text files using the standard text-based model."""
        try:
            # Read the content of the text file
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
        except UnicodeDecodeError:
            # Fallback in case of encoding issues
            with open(file_path, 'r', encoding='latin-1') as file:
                file_content = file.read()

        try:
            # Generate a summary of the file content
            summary = self.generate_file_summary(file_content)
            await self.send_message_in_chunks(message.channel, summary)

            # Log the file summary as conversational memory
            self.save_memory(
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                user_id=self.bot.user.id,
                username=self.bot_name,
                role="assistant",
                content=summary,
                session_id=session_id,
                context="file_review_response",
                memory_type='TEXT_REVIEW'
            )
        except Exception as e:
            self.log_event('ERROR', f"Error processing text file: {str(e)}")
            await message.channel.send(f"❌ Oops, there was an issue reading the file: {str(e)}")

    def generate_file_summary(self, content):
        """Generates a brief summary of the file content."""
        # Split the content into lines and get the first 10 lines or fewer
        lines = content.splitlines()
        summary_lines = lines[:10] if len(lines) > 10 else lines
        summary = "\n".join(summary_lines)
        if len(lines) > 10:
            summary += "\n... (truncated)"
        return summary

    async def handle_list_files(self, message):
        """Handles listing all files in the guild-specific folder."""
        guild_id = message.guild.id  # Get the guild's ID
        guild_folder = self.uploaded_files_directory / str(guild_id)

        if not guild_folder.exists():
            await message.channel.send(f"❌ No files found in the folder for this guild.")
            return

        # List all files in the guild folder
        files = [f for f in guild_folder.iterdir() if f.is_file()]

        if files:
            file_list = "\n".join([file.name for file in files])
            await message.channel.send(f"📜 Here are the available files for this guild:\n{file_list}")

            # Log the file listing action in logs table
            self.log_event(
                log_type="FILE_LIST",
                message=f"Files listed by {message.author.name} (User ID: {message.author.id}) in Guild ID: {guild_id}. Files: {', '.join([file.name for file in files])}.",
                guild_id=guild_id,
                user_id=message.author.id,
                username=message.author.name
            )
        else:
            await message.channel.send(f"❌ No files found.")

    async def handle_delete_file(self, message):
        """Handles the deletion of a specific uploaded file."""
        guild_id = message.guild.id  # Get the guild's ID
        guild_folder = self.uploaded_files_directory / str(guild_id)

        if not guild_folder.exists():
            await message.channel.send(f"❌ No files found in the folder for this guild. Please upload a file first.")
            return

        # Extract the file name to delete from the message content
        match = re.search(r'delete the ([\w\-\_\.]+)\s*file', message.content.lower())
        if match:
            file_name = match.group(1).lower()
        else:
            await message.channel.send(f"❌ I couldn't find a valid file name in your request.")
            return

        # Get a list of files in the guild folder
        files = [f.name.lower() for f in guild_folder.iterdir() if f.is_file()]
        base_files = [os.path.splitext(f)[0] for f in files]

        if not base_files:
            await message.channel.send(f"❌ No files available to delete.")
            return

        # Find the closest match to the file name provided by the user
        closest_match = difflib.get_close_matches(file_name, base_files, n=1, cutoff=0.6)
        if closest_match:
            matched_file = closest_match[0]
            file_path = guild_folder / next(f for f in files if f.startswith(matched_file))
            file_name_found = file_path.name
        else:
            await message.channel.send(f"❌ I couldn't find a close match for the file.")
            return

        try:
            # Delete the matched file
            file_path.unlink()
            await message.channel.send(f"🗑️ The file **{file_name_found}** has been deleted.")

            # Log the file deletion action in logs table
            self.log_event(
                log_type="FILE_DELETE",
                message=f"File {file_name_found} deleted by {message.author.name} (User ID: {message.author.id}) in Guild ID: {guild_id}.",
                guild_id=guild_id,
                user_id=message.author.id,
                username=message.author.name
            )
        except Exception as e:
            self.log_event('ERROR', f"Error deleting file: {str(e)}")
            await message.channel.send(f"❌ Oops, there was an issue while deleting the file: {str(e)}")

# Function to set up the cog
async def setup(bot):
    """Adds the AURA cog to the bot."""
    await bot.add_cog(AURACog(bot))
