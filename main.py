import os
import discord
import re
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from myserver import server_on
# ================= TOKEN =================
# Token อยู่ใน render
# ================= ID CHANNEL =================
DOT_CHANNEL_ID = 1470997086068805715  # ห้องจุดเช็คยศ
LOG_CHANNEL_ID = 1480097222614974535  # ห้อง embed เตือน/แบน
# ================= ID ROLE =================
ROLE_ID = 1479026080944885780  # ยศปุ่มรับยศ
WHITELIST_ROLE_IDS = [1474002697077264424, 1470443370538074214, 1049290191778623549,
                      1474034129841553450]  # ยศที่อนุญาตให้ส่งลิงก์ได้ (เช่น Admin/Mod)
OWNER_ID = 848068744303083551

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# เก็บจำนวนครั้งที่เตือน
user_last_messages = {}
link_warnings = {}
badword_warnings = {}
bad_words = set()
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
    if ctx.author.id != OWNER_ID:
        return

    embed = discord.Embed(
        title="<a:1bow:1475397909301432432> อ่านกฎโซนให้เข้าใจก่อนรับยศ",
        description="```กดปุ่มอีโมจิ 🔞 ด้านล่างเพื่อรับยศ```",
        color=discord.Color.purple()
    )

    await ctx.send(embed=embed, view=RoleButton())

# =========================
# ฟังก์ชันตรวจลิงก์ (รองรับ forward + embed)
# =========================

async def contains_blocked_link(msg):
    def check_text(text):
        if not text:
            return False

        text = str(text).lower()
        no_space = text.replace(" ", "")

        patterns = [
            # Discord invite
            r"discord\s*\.?\s*gg/[a-zA-Z0-9]+",
            r"discord\s*\.?\s*com/invite/[a-zA-Z0-9]+",
            r"discordapp\s*\.?\s*com/invite/[a-zA-Z0-9]+",
            
            # URL Shorteners
            r"(?:https?:\/\/)?(?:www\.)?bit\.ly\/\S+",
            r"(?:https?:\/\/)?(?:www\.)?tinyurl\.com\/\S+",
            r"(?:https?:\/\/)?(?:www\.)?is\.gd\/\S+",
            r"(?:https?:\/\/)?(?:www\.)?cutt\.ly\/\S+",
            r"(?:https?:\/\/)?(?:www\.)?t\.co\/\S+",
            r"(?:https?:\/\/)?(?:www\.)?goo\.gl\/\S+",
            r"(?:https?:\/\/)?(?:www\.)?shorturl\.at\/\S+",
        ]

        for p in patterns:
            if re.search(p, no_space):
                return True

        return False

    # 🔹 1. content
    if check_text(msg.content):
        return True

    # 🔹 2. embeds
    for emb in msg.embeds:

        if check_text(emb.title):
            return True

        if check_text(emb.description):
            return True

        if emb.url and check_text(emb.url):
            return True

        if emb.author and emb.author.url and check_text(emb.author.url):
            return True

        if emb.footer and check_text(emb.footer.text):
            return True

        for field in emb.fields:
            if check_text(field.name) or check_text(field.value):
                return True

    # 🔹 3. attachments
    # อนุญาตให้ส่งรูปและคลิปได้

    return False


# ========================
# on_message ระบบกันลิงก์ + สแปม + คำต้องห้าม
# ========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return

    if any(role.id in WHITELIST_ROLE_IDS for role in message.author.roles):
        await bot.process_commands(message)
        return

        # =========================
        # DOT ห้องพิมพ์ได้แค่ "."
        # =========================

    if message.channel.id == DOT_CHANNEL_ID:

        # ถ้าไม่ใช่ "."
        if (
                message.content.strip() != "."
                or message.mentions
                or message.stickers
                or message.attachments
                or message.embeds
        ):
            await message.delete()

            warn_embed = discord.Embed(
                description="<a:warning2:1477146378491793529> คุณกระทำผิดกฎเซิร์ฟเวอร์\n```โปรดพิมพ์เพียงจุดเพื่อเช็คยศ```",
                color=discord.Color.orange()
            )

            await message.channel.send(
                message.author.mention,
                embed=warn_embed,
                delete_after=5
            )

            return

        return
    # ========================================
    #  LINK ระบบกันลิ้งก์ข้อความตอบกลับ + embed + ban
    # ========================================
    if await contains_blocked_link(message):

        await message.delete()

        user_id = message.author.id
        log_channel = bot.get_channel(LOG_CHANNEL_ID)

        # ครั้งแรก
        if user_id not in link_warnings:
            link_warnings[user_id] = 1

            warn_embed = discord.Embed(
                description="<a:warning2:1477146378491793529> คุณส่งลิงก์ที่ไม่ได้รับอนุญาต\n```คุณถูก Timeout 24 ชั่วโมง\nหากทำผิดซ้ำจะถูกแบนถาวร```",
                color=discord.Color.orange()
            )

            await message.channel.send(
                message.author.mention,
                embed=warn_embed,
                delete_after=5
            )

            await message.author.timeout(
                timedelta(days=1),
                reason="ส่งลิงก์ต้องห้าม"
            )

            if log_channel:
                log = discord.Embed(
                    title="<a:alert:1473532424095797308> __ผู้ใช้ทำผิดกฏเซิร์ฟเวอร์__ <a:alert:1473532424095797308>",
                    color=discord.Color.orange()
                )

                log.add_field(name=" ", value=f"**`👤 ผู้ใช้ :`** {message.author.mention}", inline=False)
                log.add_field(name=" ", value=f"**`🏷️ ห้อง :`** {message.channel.mention}", inline=False)
                log.add_field(name=" ", value=f"**`📜 เหตุผล :`** ***__ส่งลิงก์ต้องห้าม__***", inline=False)
                log.add_field(name=" ",
                              value=f"**`🔨 บทลงโทษ :`** ***__เตือนครั้งที่ 1__*** <a:1red:1475382252715380887>",
                              inline=False)

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

            return
        # ========================
        # แบนถ้าทำซ้ำ
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
                ban_embed.add_field(name=" ", value=f"**`📜 เหตุผล :`** ***__ส่งลิงก์ต้องห้ามซ้ำ__***", inline=False)

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

    # 👇 เริ่มกันสแปม

    # =========================
    # SPAM กันสแปมข้อความแพทเทิร์นเดิม
    # =========================
    user_id = message.author.id
    content = message.content.strip().lower()

    if user_id not in user_last_messages:
        user_last_messages[user_id] = []

    user_last_messages[user_id].append((content, message))

    # เก็บแค่ 2 ล่าสุด
    if len(user_last_messages[user_id]) > 2:
        user_last_messages[user_id].pop(0)

    # เช็คว่าทั้ง 2 เหมือนกันมั้ย
    if len(user_last_messages[user_id]) == 2:
        msgs = user_last_messages[user_id]

        if all(m[0] == content for m in msgs):
            for _, msg_obj in msgs:
                try:
                    await msg_obj.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    pass

            user_last_messages[user_id] = []

            await message.channel.send(
                f"{message.author.mention}",
                embed=discord.Embed(
                    description="<a:warning2:1477146378491793529> คุณกระทำผิดกฎเซิร์ฟเวอร์\n```ห้ามสแปมข้อความซ้ำ 🚫```",
                    color=discord.Color.orange()
                ),
                delete_after=5
            )
            return

    # =========================
    #  BADWORD ระบบกันคำหยาบหรือคำต้องห้าม
    # =========================
    def contains_bad_word(text):
        if not text:
            return False

        text = text.lower()

        for word in bad_words:
            if word in text:
                return True

        return False

    if contains_bad_word(message.content):

        await message.delete()

        user_id = message.author.id
        log_channel = bot.get_channel(LOG_CHANNEL_ID)

        # ========================
        # ครั้งแรก = เตือน
        # ========================
        if user_id not in badword_warnings:

            badword_warnings[user_id] = 1

            warn_embed = discord.Embed(
                description="<a:warning2:1477146378491793529> คุณกระทำผิดกฎเซิร์ฟเวอร์\n```พิมพ์คำต้องห้ามหรือคำหยาบ```",
                color=discord.Color.orange()
            )

            await message.channel.send(
                message.author.mention,
                embed=warn_embed,
                delete_after=5
            )

            if log_channel:
                log = discord.Embed(
                    title="<a:alert:1473532424095797308> __ผู้ใช้ทำผิดกฏเซิร์ฟเวอร์__ <a:alert:1473532424095797308>",
                    color=discord.Color.orange()
                )

                log.add_field(name=" ", value=f"**`👤 ผู้ใช้ :`** {message.author.mention}", inline=False)
                log.add_field(name=" ", value=f"**`🏷️ ห้อง :`** {message.channel.mention}", inline=False)
                log.add_field(name=" ", value=f"**`📜 เหตุผล :`** ***__พิมพ์คำต้องห้าม/คำหยาบ__***", inline=False)
                log.add_field(name=" ",
                              value=f"**`🔨 บทลงโทษ :`** ***__เตือนครั้งที่ 1__*** <a:1red:1475382252715380887>",
                              inline=False)

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

            return

        # ========================
        # ครั้งสอง = แบน
        # ========================
        else:

            await message.guild.ban(
                message.author,
                reason="ใช้คำต้องห้ามซ้ำ"
            )

            if log_channel:
                ban_embed = discord.Embed(
                    title="<a:alert:1473532424095797308> __ผู้ใช้ถูกแบนถาวร__ 🔨",
                    color=discord.Color.red()
                )

                ban_embed.add_field(name=" ", value=f"**`👤 ผู้ใช้ :`** {message.author.mention}", inline=False)
                ban_embed.add_field(name=" ", value=f"**`🏷️ ห้อง :`** {message.channel.mention}", inline=False)
                ban_embed.add_field(name=" ", value=f"**`👮 แบนโดย :`** {bot.user.mention}", inline=False)
                ban_embed.add_field(name=" ", value=f"**`📜 เหตุผล :`** ***__พิมพ์คำต้องห้ามซ้ำ__***", inline=False)

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
        ban_embed.add_field(name=" ", value=f"**`📜 เหตุผล :`** {reason}", inline=False)

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

    if await contains_blocked_link(after):
        await after.delete()

        warn_embed = discord.Embed(
            description="<a:warning2:1477146378491793529> คุณกระทำผิดกฎเซิร์ฟเวอร์\n```ห้ามแก้ข้อความเป็นลิงก์ 🚫```",
            color=discord.Color.orange()
        )

        await after.channel.send(after.author.mention, embed=warn_embed, delete_after=5)


# ========================
# ระบบนำ warning ออกจากผู้ใช้
# ========================

@bot.command()
async def clearwarn(ctx, member: discord.Member):
    if ctx.author.id != OWNER_ID:
        return

    had_warning = (
            member.id in link_warnings or
            member.id in badword_warnings
    )

    # ลบ warning
    link_warnings.pop(member.id, None)
    badword_warnings.pop(member.id, None)

    try:
        await member.timeout(
            None,
            reason=f"ปลด Timeout โดย {ctx.author}"
        )
    except discord.Forbidden:
        pass

    if had_warning:
        result_embed = discord.Embed(
            title="✅ รีเซ็ตการเตือนแล้ว",
            description=f"ผู้ใช้: {member.mention}\nสถานะ: ไม่มีการเตือนแล้ว",
            color=discord.Color.green()
        )
    else:
        result_embed = discord.Embed(
            title="ℹ️ ไม่มีการเตือน",
            description=f"{member.mention} ยังไม่เคยโดนเตือน",
            color=discord.Color.blue()
        )

    await ctx.send(embed=result_embed)


# ============ เพิ่มคำต้องห้าม =============
@bot.command()
async def addword(ctx, *, word):
    if ctx.author.id != OWNER_ID:
        return

    word = word.lower()

    if word in bad_words:
        await ctx.send(f"มีคำนี้อยู่แล้ว: `{word}`")
        return

    bad_words.add(word)

    await ctx.send(f"เพิ่มคำต้องห้าม: `{word}`")


# ============ ลบคำต้องห้าม =============
@bot.command()
async def removeword(ctx, *, word):
    if ctx.author.id != OWNER_ID:
        return

    bad_words.discard(word.lower())

    await ctx.send(f"ลบคำต้องห้าม: `{word}`")


# ============ LIST คำต้องห้าม =============
@bot.command()
async def listword(ctx):
    if ctx.author.id != OWNER_ID:
        return

    if not bad_words:
        list_embed = discord.Embed(
            title="📄 รายการคำต้องห้าม",
            description="ยังไม่มีคำต้องห้าม",
            color=discord.Color.blue()
        )
    else:
        word_list = "\n".join(f"- {word}" for word in bad_words)

        list_embed = discord.Embed(
            title="📄 รายการคำต้องห้าม",
            description=word_list,
            color=discord.Color.orange()
        )

    await ctx.send(embed=list_embed)


# ================= RUN =================

server_on()

bot.run(os.getenv('TOKEN'))
