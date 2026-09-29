import discord
from discord import app_commands
from discord.ext import commands


# نافذة عرض الأزرار المتعددة المخصصة
class CustomMultiButtonsView(discord.ui.View):

    def __init__(self, buttons_data):
        super().__init__(timeout=None)  # الأزرار لا تنتهي أبداً

        for label, hidden_text in buttons_data:
            if label and hidden_text:
                button = discord.ui.Button(
                    label=label[:80],  # ديسكورد يسمح بـ 80 حرف كحد أقصى لاسم الزر
                    style=discord.ButtonStyle.primary,
                    emoji="📌",
                )
                button.callback = self.create_callback(hidden_text)
                self.add_item(button)

    def create_callback(self, hidden_text):
        async def button_callback(interaction: discord.Interaction):
            # الرسالة السرية لكل زر
            await interaction.response.send_message(
                content=hidden_text, ephemeral=True
            )

        return button_callback


# نافذة إدخال مخصصة مع ملاحظة إرشادية داخل خانة الكتابة
class CustomMultiModal(discord.ui.Modal, title="إنشاء إيمبد مع أزرار مخصصة"):

    def __init__(self, embed_title: str, embed_desc: str):
        super().__init__()
        self.embed_title = embed_title
        self.embed_desc = embed_desc

    # خانة الكتابة مع ملاحظة إرشادية بخط خفيف لتذكرك دائماً
    buttons_input = discord.ui.TextInput(
        label="اكتب الأزرار هنا (كل زر في سطر)",
        style=discord.TextStyle.paragraph,
        placeholder=(
            "⚠️ ملاحظة للتذكير: اكتب هكذا (اسم الزر : النص السري)\n"
            "مثال:\n"
            "القوانين : ممنوع السب أو الإزعاج\n"
            "الدعم الفني : تواصل معنا هنا"
        ),
        required=True,
        max_length=2000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        raw_text = self.buttons_input.value

        # تحليل النص واستخراج الأسماء والنصوص السرية
        buttons_data = []
        lines = raw_text.split("\n")
        for line in lines:
            # تجاهل أسطر الملاحظات لو المستخدم كتبها أو نسحها بالخطأ
            if "⚠️" in line or "ملاحظة" in line or "مثال:" in line:
                continue

            if ":" in line:
                parts = line.split(":", 1)
                label = parts[0].strip()
                text = parts[1].strip()
                if label and text:
                    buttons_data.append((label, text))

        if not buttons_data:
            await interaction.response.send_message(
                "❌ خطأ: يرجى كتابة الأزرار بالشكل الصحيح (الاسم : النص السري)",
                ephemeral=True,
            )
            return

        if len(buttons_data) > 5:
            await interaction.response.send_message(
                "❌ عذراً، الحد الأقصى في هذه النافذة هو 5 أزرار لتسهيل الكتابة!",
                ephemeral=True,
            )
            return

        # بناء الإيمبد
        embed = discord.Embed(
            title=self.embed_title,
            description=self.embed_desc,
            color=discord.Color.from_rgb(88, 101, 242),
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_footer(
            text=f"تم الإرسال بواسطة: {interaction.user.name}",
            icon_url=(
                interaction.user.avatar.url
                if interaction.user.avatar
                else None
            ),
        )

        # إنشاء الأزرار وإرسالها
        view = CustomMultiButtonsView(buttons_data)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ تم نشر الإيمبد ومعه ({len(buttons_data)}) أزرار مخصصة بنجاح!",
            ephemeral=True,
        )


class EmbedBuilder(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="إنشاء_إيمبد_بأزرار",
        description=(
            "[إدارة السيرفر] إرسال إيمبد مع أزرار متعددة تحدد أسماءها ونصوصها"
        ),
    )
    @app_commands.describe(
        العنوان="عنوان الإيمبد الرئيسي", الوصف="محتوى ووصف الإيمبد"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def create_embed(
        self, interaction: discord.Interaction, العنوان: str, الوصف: str
    ):
        await interaction.response.send_modal(
            CustomMultiModal(العنوان, الوصف)
        )


async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))