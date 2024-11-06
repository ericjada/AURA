import discord
from discord.ext import commands
import os
import asyncio
import torch
import pathlib
import logging
from asyncio import Semaphore
from typing import Optional
from PIL import Image
import uuid
import sqlite3
from datetime import datetime
from diffusers import StableDiffusion3Pipeline
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger('ImageGenerator')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='imagegenerator.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Directory for saving generated images
IMAGE_SAVE_DIRECTORY = r"C:\Users\ericj\Documents\GitHub\DiscordBot\AURADiscordBot\AURA\generated_images"
os.makedirs(IMAGE_SAVE_DIRECTORY, exist_ok=True)

# Add after other initial setup code
load_dotenv('token.env')
HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN')

class ImageGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model_path = "stabilityai/stable-diffusion-3-medium-diffusers"
        self.model_loaded = False
        self.semaphore = Semaphore(2)
        self.pipe = None

        self.db_path = pathlib.Path('./imagegenerator.db')
        self.setup_database()

        asyncio.create_task(self.load_model())

    def setup_database(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            with conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        log_type TEXT NOT NULL,
                        log_message TEXT NOT NULL,
                        guild_id INTEGER,
                        channel_id INTEGER,
                        user_id INTEGER,
                        username TEXT,
                        timestamp TEXT NOT NULL
                    )
                ''')
            logger.info("Database setup completed.")
        finally:
            conn.close()

    def log_event(self, log_type, message, guild_id=None, channel_id=None, user_id=None, username=None):
        conn = sqlite3.connect(str(self.db_path))
        timestamp = datetime.now().isoformat()
        with conn:
            conn.execute('''
                INSERT INTO logs (log_type, log_message, guild_id, channel_id, user_id, username, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (log_type, message, guild_id, channel_id, user_id, username, timestamp))
        conn.close()
        logger.info(f"Logged event: {log_type} - {message}")

    async def load_model(self):
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Stable Diffusion model from {self.model_path} on {device}...")
            
            # Add more detailed logging about system state
            logger.info(f"CUDA available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")
                logger.info(f"CUDA memory allocated: {torch.cuda.memory_allocated(0)}")
            
            self.pipe = StableDiffusion3Pipeline.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                use_safetensors=True,
                variant="fp16" if torch.cuda.is_available() else None,
                token=HUGGINGFACE_TOKEN
            ).to(device)

            # Enable memory efficient attention if using CUDA
            if torch.cuda.is_available():
                self.pipe.enable_attention_slicing()
                self.pipe.enable_vae_slicing()
            
            self.model_loaded = True
            logger.info("Stable Diffusion model loaded successfully.")
            self.log_event("MODEL_LOAD", f"Stable Diffusion model loaded on device: {device}")
        except Exception as e:
            logger.error(f"Failed to load Stable Diffusion model: {str(e)}")
            logger.exception("Detailed error traceback:")  # This will log the full traceback
            self.log_event("MODEL_LOAD_FAILURE", f"Failed to load Stable Diffusion model: {str(e)}")
            self.model_loaded = False  # Ensure this is set to False on failure

    @discord.app_commands.command(
        name="generate_image",
        description="Generate an image based on your prompt using the Stable Diffusion model."
    )
    async def generate_image(
        self,
        interaction: discord.Interaction,
        prompt: str,
        num_inference_steps: Optional[int] = 50,
        guidance_scale: Optional[float] = 7.5
    ):
        if not self.model_loaded or self.pipe is None:
            await interaction.response.send_message("❌ The image generation model is still loading. Please try again in a few seconds.")
            return

        # Input validation
        try:
            num_inference_steps = int(num_inference_steps)
            guidance_scale = float(guidance_scale)
        except ValueError:
            await interaction.response.send_message("❌ Invalid parameter values provided.")
            return

        # Only send the "generating" message if all checks pass
        await interaction.response.send_message("⏳ Generating your image... This might take a while.")

        guild_id = interaction.guild.id if interaction.guild else None
        channel_id = interaction.channel.id if interaction.guild else None
        user_id = interaction.user.id
        username = interaction.user.name

        logger.info(f"Received image generation request from {username} (ID: {user_id}) with prompt: {prompt}")
        self.log_event("COMMAND_INVOKED", f"User {username} invoked /generate_image with prompt: {prompt}", guild_id, channel_id, user_id, username)

        try:
            async with self.semaphore:
                logger.info(f"Generating image for user {username} with prompt: {prompt}")
                self.log_event("IMAGE_GENERATION_STARTED", f"Image generation started for prompt: {prompt}", guild_id, channel_id, user_id, username)

                image = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.pipe(prompt, num_inference_steps=num_inference_steps, guidance_scale=guidance_scale).images[0]
                )

                # Generate a unique filename
                unique_filename = f"{uuid.uuid4()}.png"
                image_save_path = os.path.join(IMAGE_SAVE_DIRECTORY, unique_filename)
                image.save(image_save_path, format="PNG")

                logger.info(f"Image generated and saved to {image_save_path}")
                self.log_event("IMAGE_GENERATION_SUCCESS", f"Image generated and saved to {image_save_path}", guild_id, channel_id, user_id, username)

            await interaction.channel.send(f"✅ Your image has been generated!", file=discord.File(image_save_path))
            logger.info(f"Sent generated image to user {username}")
            self.log_event("IMAGE_SENT", f"Sent image to user: {image_save_path}", guild_id, channel_id, user_id, username)

        except Exception as e:
            logger.error(f"Error during image generation: {str(e)}")
            self.log_event("IMAGE_GENERATION_ERROR", f"Error during image generation: {str(e)}", guild_id, channel_id, user_id, username)
            await interaction.channel.send(f"❌ An error occurred while generating the image: {str(e)}")

# Function to set up the cog
async def setup(bot):
    await bot.add_cog(ImageGenerator(bot))
