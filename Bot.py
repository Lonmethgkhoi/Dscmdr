import os
import discord
from discord.ext import commands
from discord import app_commands
from openai import OpenAI

# ----------------------------
# 🔧 CẤU HÌNH
# ----------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # Token bot Discord
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # API key Pella
LOG_CHANNEL_NAME = "mod-logs"  # tên kênh log vi phạm

# Client Pella (OpenAI API style)
client_ai = OpenAI(api_key=OPENAI_API_KEY)

# Intent để bắt message + member
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Bot
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------------
# 🎉 EVENTS
# ----------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập thành công: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Đã sync {len(synced)} slash commands.")
    except Exception as e:
        print(f"Lỗi sync command: {e}")

# ----------------------------
# 🛡️ AUTO MODERATION
# ----------------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    try:
        # Gọi GPT check vi phạm
        resp = client_ai.chat.completions.create(
            model="gpt-4.1-mini",  # free model
            messages=[
                {"role": "system", "content": "You are a Discord moderation AI. Rate severity of rule violations (0=ok, 1=warn, 2=kick, 3=ban)."},
                {"role": "user", "content": message.content}
            ],
            max_tokens=50,
        )

        verdict = resp.choices[0].message.content.strip()
        print(f"[MODERATION] {message.author}: {verdict}")

        # tìm kênh log
        log_channel = discord.utils.get(message.guild.text_channels, name=LOG_CHANNEL_NAME)
        action = None

        if "1" in verdict:
            action = f"⚠️ {message.author} bị cảnh cáo"
            await message.channel.send(f"⚠️ {message.author.mention} vi phạm nhẹ → Cảnh cáo.")

        elif "2" in verdict:
            action = f"⛔ {message.author} bị kick"
            try:
                await message.author.kick(reason="Moderation AI: Vi phạm nặng")
                await message.channel.send(f"⛔ {message.author.mention} đã bị **kick** khỏi server.")
            except discord.Forbidden:
                action = f"⚠️ Không đủ quyền kick {message.author}"
                await message.channel.send("❌ Bot không có quyền kick thành viên này.")

        elif "3" in verdict:
            action = f"🚫 {message.author} bị ban"
            try:
                await message.author.ban(reason="Moderation AI: Vi phạm rất nặng")
                await message.channel.send(f"🚫 {message.author.mention} đã bị **ban** khỏi server.")
            except discord.Forbidden:
                action = f"⚠️ Không đủ quyền ban {message.author}"
                await message.channel.send("❌ Bot không có quyền ban thành viên này.")

        else:
            action = f"✅ {message.author} không vi phạm"

        # Ghi log
        if log_channel and action:
            await log_channel.send(
                f"[MOD] {action}\n💬 Nội dung: {message.content}\n📊 Verdict: {verdict}"
            )

    except Exception as e:
        print(f"Lỗi moderation: {e}")

    await bot.process_commands(message)

# ----------------------------
# 🎭 LỆNH VUI
# ----------------------------
@bot.tree.command(name="jokeoftheday", description="Nhận 1 câu đùa vui từ AI")
async def jokeoftheday(interaction: discord.Interaction):
    try:
        resp = client_ai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a funny bot. Tell a short joke."}
            ],
            max_tokens=50,
        )
        joke = resp.choices[0].message.content.strip()
        await interaction.response.send_message(f"😂 Joke of the day: {joke}")
    except Exception as e:
        await interaction.response.send_message("❌ Lỗi khi lấy joke.")
        print(f"Lỗi joke: {e}")

# ----------------------------
# 🚀 RUN BOT
# ----------------------------
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
