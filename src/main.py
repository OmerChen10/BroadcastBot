import os
import discord
from discord.ext import commands
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import threading


class BroadcastBot:
    def __init__(self, token: str, user_ids: list[int], port: int = 8000):
        self.token = token
        self.user_ids = user_ids
        self.port = port
        self.last_ip = None

        # Discord setup
        intents = discord.Intents.default()
        self.bot = commands.Bot(command_prefix="!", intents=intents)

        @self.bot.event
        async def on_ready():
            print(f"Bot is online as {self.bot.user}")

        # FastAPI setup
        self.app = FastAPI()

        @self.app.post("/broadcast")
        async def broadcast(msg: str = Query(..., description="Message to broadcast")):
            if not msg:
                return JSONResponse(
                    {"status": "error", "message": "Missing 'msg' parameter"},
                    status_code=400
                )

            # Schedule the coroutine on the bot's event loop
            future = asyncio.run_coroutine_threadsafe(
                self.broadcast_message(msg), self.bot.loop
            )
            failed_users = future.result()  # Wait for result

            if failed_users:
                return JSONResponse(
                    {"status": "partial_success", "message": f"Failed to send to users: {failed_users}"},
                    status_code=207
                )
            return JSONResponse(
                {"status": "success", "message": "Message broadcasted"},
                status_code=200
            )

    async def broadcast_message(self, msg: str):
        """Send a message to all specified users."""
        failed_users = []
        for user_id in self.user_ids:
            user = await self.bot.fetch_user(user_id)
            if user:
                try:
                    await user.send(msg)
                    print(f"Sent message to {user.name}")
                except Exception as e:
                    print(f"Failed to send message to {user.name}: {e}")
                    failed_users.append(user_id)
            else:
                print(f"User with ID {user_id} not found")
        
        return failed_users

    def run_fastapi(self):
        """Run FastAPI in a background thread."""
        uvicorn.run(self.app, host="0.0.0.0", port=self.port, log_level="info")

    def run(self):
        """Start FastAPI + Discord bot."""
        threading.Thread(target=self.run_fastapi, daemon=True).start()
        self.bot.run(self.token)


# === MAIN ===
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    USER_IDS = os.getenv("DISCORD_USER_IDS", "")

    if not TOKEN:
        raise ValueError("Missing DISCORD_BOT_TOKEN environment variable")

    if not USER_IDS:
        raise ValueError("Missing DISCORD_USER_IDS environment variable")

    # Convert comma-separated list into integers
    USER_IDS = [int(uid.strip()) for uid in USER_IDS.split(",") if uid.strip()]

    PORT = int(os.getenv("PORT", "8000"))

    bot = BroadcastBot(TOKEN, USER_IDS, port=PORT)
    bot.run()
