import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from myserver import server_on

# ================= TOKEN =================
# Token อยู่ใน render
# ================= CONFIG =================

ROLE_ID = 1479026080944885780        # ยศปุ่มรับยศ
CHANNEL_ID = 1479054661192384562     # ห้องที่ใช้ส่งปุ่มรับยศ (ไม่จำเป็นต้องใช้ก็ได้)
LOG_CHANNEL_ID = 1480097222614974535  # ห้อง log
WHITELIST_ROLE_IDS = [1474002697077264424, 1470443370538074214, 1049290191778623549, 1474034129841553450]  # ยศที่อนุญาตให้ส่งลิงก์ได้ (เช่น Admin/Mod)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# เก็บจำนวนครั้งที่เตือน
warnings = {}

# ลิงก์ต้องห้าม
blocked_links = [
    "https://",
    "http://",
    "discord.gg/",
    "discord.com/invite",
    "discordapp.com/invite",
    "t.me",
    "line.me",
    "is.gd",
    "bit.ly",
    "tinyurl.com"
]

# ========================
# ปุ่มรับยศ
# ========================
class RoleButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔞 รับยศโซน18", style=discord.ButtonStyle.green)
    async def get_role(self, interaction: discord.Interaction, _button: discord.ui.Button):

        role = interaction.guild.get_role(ROLE_ID)

        if role in interaction.user.roles:

            embed = discord.Embed(
                description=f"<a:wrong1:1477677468327350414> คุณได้รับยศ {role.mention} ไปแล้ว!!",
                color=discord.Color.red()
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            await interaction.user.add_roles(role)

            embed = discord.Embed(
                description=f"<a:correct_green:1479805579504386165> คุณได้รับยศ {role.mention} แล้ว!!",
                color=discord.Color.green()
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)


# ========================
# บอทออนไลน์
# ========================
@bot.event
async def on_ready():
    print(f"บอทออนไลน์ {bot.user}")


# ========================
# คำสั่งส่งปุ่มรับยศ
# ========================
@bot.command()
async def sendrole(ctx):

    if ctx.author.guild_permissions.administrator:

        embed = discord.Embed(
            title="<a:1bow:1475397909301432432> อ่านกฎโซนให้เข้าใจก่อนรับยศ",
            description="```กดปุ่มอีโมจิ 🔞 ด้านล่างเพื่อรับยศ```",
            color=discord.Color.purple()
        )

        await ctx.send(embed=embed, view=RoleButton())


# ========================
# ระบบกันลิงก์
# ========================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # ไม่ตรวจ admin
    if message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return

    # ไม่ตรวจ role ที่ whitelist
    if any(role.id in WHITELIST_ROLE_IDS for role in message.author.roles):
        await bot.process_commands(message)
        return

    content = message.content.lower()

    # ตรวจลิงก์ในข้อความ
    if any(link in content for link in blocked_links):

        await message.delete()

        user_id = message.author.id
        log_channel = bot.get_channel(LOG_CHANNEL_ID)

        # ครั้งแรก
        if user_id not in warnings:

            warnings[user_id] = 1

            warn_embed = discord.Embed(
                description="<a:warning2:1477146378491793529> คุณส่งลิงก์ที่ไม่ได้รับอนุญาต\n```ครั้งต่อไปคุณจะถูกแบนถาวร```",
                color=discord.Color.orange()
            )

            await message.channel.send(
                message.author.mention,
                embed=warn_embed,
                delete_after=5
            )

            if log_channel:
                log = discord.Embed(
                    title="<a:alert:1473532424095797308> __ตรวจพบมีผู้ใช้ส่งลิงก์ต้องห้าม__ <a:alert:1473532424095797308>",
                    color=discord.Color.orange()
                )

                log.add_field(name=" ", value=f"**`👤 ผู้ใช้ :`** {message.author.mention}", inline=False)
                log.add_field(name=" ", value=f"**`🏷️ ห้อง :`** {message.channel.mention}", inline=False)
                log.add_field(name=" ",value=f"**`📜 บทลงโทษ :`** ***__เตือนครั้งที่ 1__*** <a:1red:1475382252715380887>",inline=False)

                log.set_author(
                    name=message.author.name,
                    icon_url=message.author.display_avatar.url
                )

                log.set_thumbnail(
                    url=message.author.display_avatar.url
                )

                log.set_image(
                    url="https://i.postimg.cc/nh16Vmsb/standard.gif"
                )

                thai_time = message.created_at + timedelta(hours=7)

                log.set_footer(
                    text=f"{message.guild.name} • {thai_time.strftime('%d/%m/%Y %H:%M')}",
                    icon_url=message.guild.icon.url if message.guild.icon else None
                )

                await log_channel.send(embed=log)

        # ========================
        # ระบบแบนโดยบอท
        # ========================

        else:

            await message.guild.ban(
                message.author,
                reason="ส่งลิงก์ต้องห้ามซ้ำ"
            )

            if log_channel:
                ban_embed = discord.Embed(
                    title="<a:alert:1473532424095797308> __ผู้ใช้ถูกแบนถาวร__ 🔨",
                    color=discord.Color.red()
                )

                ban_embed.add_field(name=" ", value=f"**`👤 ผู้ใช้ :`** {message.author.mention}", inline=False)
                ban_embed.add_field(name=" ", value=f"**`🏷️ ห้อง :`** {message.channel.mention}", inline=False)
                ban_embed.add_field(name=" ", value=f"**`👮 แบนโดย :`** {bot.user.mention}", inline=False)
                ban_embed.add_field(name=" ", value=f"**`📜 บทลงโทษ :`** ***__ส่งลิงก์ต้องห้ามซ้ำ__***", inline=False)

                ban_embed.set_author(
                    name=message.author.name,
                    icon_url=message.author.display_avatar.url
                )

                ban_embed.set_thumbnail(
                    url=message.author.display_avatar.url
                )

                ban_embed.set_image(
                    url="https://i.postimg.cc/xTwZ3RmN/standard-(1).gif"
                )

                thai_time = message.created_at + timedelta(hours=7)

                ban_embed.set_footer(
                    text=f"{message.guild.name} • {thai_time.strftime('%d/%m/%Y %H:%M')}",
                    icon_url=message.guild.icon.url if message.guild.icon else None
                )

                await log_channel.send(embed=ban_embed)

            return

        await bot.process_commands(message)

# ========================
# ระบบแบนโดยแอดมิน
# ========================

@bot.event
async def on_member_ban(guild, user):

    log_channel = bot.get_channel(LOG_CHANNEL_ID)

    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):

        moderator = entry.user

        # ถ้าบอทเป็นคนแบน ไม่ต้องส่ง log ซ้ำ
        if moderator == bot.user:
            return

        reason = entry.reason if entry.reason else "ไม่ได้ระบุเหตุผล"

        ban_embed = discord.Embed(
            title="<a:alert:1473532424095797308> __ผู้ใช้ถูกแบนถาวร__ 🔨",
            color=discord.Color.red()
        )

        ban_embed.add_field(name=" ", value=f"**`👤 ผู้ใช้ :`** {user.mention}", inline=False)
        ban_embed.add_field(name=" ", value=f"**`🏷️ ห้อง :`** ***__ไม่ทราบเพราะแอดมินแบน__***", inline=False)
        ban_embed.add_field(name=" ", value=f"**`👮 แบนโดย :`** {moderator.mention}", inline=False)
        ban_embed.add_field(name=" ", value=f"**`📜 บทลงโทษ :`** {reason}", inline=False)

        ban_embed.set_author(
            name=user.name,
            icon_url=user.display_avatar.url
        )

        ban_embed.set_thumbnail(
            url=user.display_avatar.url
        )

        ban_embed.set_image(
            url="https://i.postimg.cc/xTwZ3RmN/standard-(1).gif"
        )

        thai_time = datetime.now(timezone.utc) + timedelta(hours=7)

        ban_embed.set_footer(
            text=f"{guild.name} • {thai_time.strftime('%d/%m/%Y %H:%M')}",
            icon_url=guild.icon.url if guild.icon else None
        )

        if log_channel:
            await log_channel.send(embed=ban_embed)

        break

# ========================
# ระบบกันแก้ข้อตวามเป็นลิงก์
# ========================

@bot.event
async def on_message_edit(_, after):

    if after.author.bot:
        return

    if any(role.id in WHITELIST_ROLE_IDS for role in after.author.roles):
        return

    content = after.content.lower()

    if any(link in content for link in blocked_links):

        await after.delete()

        await after.channel.send(
            f"{after.author.mention} ห้ามแก้ข้อความเป็นลิงก์ 🚫",
            delete_after=5
        )

# ========================
# ระบบนำ warning ออกจากผู้ใช้
# ========================

@bot.command()
@commands.has_permissions(administrator=True)
async def clearwarn(ctx, member: discord.Member):

    if member.id in warnings:
        del warnings[member.id]

        embed = discord.Embed(
            title="✅ รีเซ็ตการเตือนแล้ว",
            description=f"ผู้ใช้: {member.mention}\nสถานะ: ไม่มีการเตือนแล้ว",
            color=discord.Color.green()
        )

    else:
        embed = discord.Embed(
            title="ℹ️ ไม่มีการเตือน",
            description=f"{member.mention} ยังไม่เคยโดนเตือน",
            color=discord.Color.blue()
        )

    await ctx.send(embed=embed)

# ================= RUN =================

server_on()


bot.run(os.getenv('TOKEN'))
