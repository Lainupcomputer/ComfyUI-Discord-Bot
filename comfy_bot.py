import os
import io
import discord
from discord import File
from discord.ext import commands
import uuid
import re
from discord.ui import View, Button

from bot_db import BotDB
from comfy_handlers_manager import ComfyHandlersManager, ComfyHandlersContext
from comfy_client import ComfyClient
from common import get_logger

intents = discord.Intents.default()
intents.dm_messages = True
bot = commands.Bot(intents=intents, command_prefix="/")
logger = get_logger("ComfyBOT")


def process_message(message):
    # TODO optimize by finding the hash tags and replace only them
    # hashtag_pattern = r'#\w+'
    # hashtags = re.findall(hashtag_pattern, message)

    prefix = ComfyHandlersContext().get_prefix(ComfyHandlersManager().get_current_handler().key())
    postfix = ComfyHandlersContext().get_postfix(ComfyHandlersManager().get_current_handler().key())
    if prefix is not None:
        message = "{} {}".format(prefix, message)
    if postfix is not None:
        message = "{} {}".format(message, postfix)

    refs = ComfyHandlersContext().get_reference(ComfyHandlersManager().get_current_handler().key())
    message = message + " "
    for key, value in refs.items():
        message = message.replace("{} ".format(key), "{} ".format(value))
    message = message[:-1]
    logger.debug("processed prompt: {}".format(message))
    return message


# Event triggered when the bot is ready
@bot.event
async def on_ready():
    logger.info(f'on_ready - logged in as {bot.user.name} bot.')


@bot.event
async def on_message(message):
    # Check if the message is from a user and not the bot itself
    if message.author == bot.user:
        return
    #
    # print(str(len(message.attachments)))
    # print(message.attachments[0].content_type)

    if len(message.attachments) > 0:
        for attachment in message.attachments:
            if attachment.content_type.startswith('image'):
                # print(attachment.url)
                pass

    if message.content.startswith("!help"):
        await message.channel.send("Hi, use '/' commands")
    # Check if the message starts with a specific command or trigger
    # async def rerun(interaction):
    #     print(interaction.custom_id)
    #     await interaction.response.send_message("")
    #
    # view = View()
    # btn = Button(label="Again!", style=discord.ButtonStyle.green, custom_id="test_button")
    # btn.callback = rerun
    # view.add_item(btn)
    # await message.channel.send("", view=view)

    # # Open the image file
    # with open("example.png", "rb") as f:
    #     picture = discord.File(f)
    #
    # # Send the message with the picture attached
    # await message.channel.send("Here's a picture!", file=picture)


@bot.slash_command(name="q", description="Submit a prompt to current workflow handler")
async def prompt(ctx, message):
    prompt_handler = ComfyHandlersManager().get_current_handler()
    p = prompt_handler.handle(process_message(message))
    await ctx.respond("Prompt received...")
    images = await ComfyClient().get_images(p, ctx, prompt_handler)

    for node_id, image_list in images.items():
        imgs = [File(filename=str(uuid.uuid4()) + ".png", fp=io.BytesIO(image_data)) for image_data in image_list]
        for img in imgs:
            await ctx.send("", file=img)

    await ctx.send("All complete")


@bot.slash_command(name="ref-set", description="Set a reference value")
async def ref_set(ctx, ref, value):
    if '#' in ref:
        await ctx.respond("\# can`t be in the given ref name!")
        return
    if ' ' in ref:
        await ctx.respond("white space can`t be in the given ref name!")
        return
    ComfyHandlersContext().set_reference(ComfyHandlersManager().get_current_handler().key(), ref, value)
    await ctx.respond("Set #{}={}".format(ref, value))


@bot.slash_command(name="ref-del", description="Remove a reference")
async def ref_del(ctx, ref):
    if '#' in ref:
        await ctx.respond('\# can`t be in the given ref name!')
        return
    if ' ' in ref:
        await ctx.respond("white space can`t be in the given ref name!")
        return
    ComfyHandlersContext().remove_reference(ComfyHandlersManager().get_current_handler().key(), ref)
    await ctx.respond("Remove #{}".format(ref))


@bot.slash_command(name="ref-view", description="View all references")
async def ref_view(ctx):
    respond = "Current references:"
    for key, value in ComfyHandlersContext().get_reference(ComfyHandlersManager().get_current_handler().key()).items():
        respond = "{}\n{} = {}".format(respond, key, value)
    await ctx.respond(respond)


@bot.slash_command(name="prefix", description="Set a prefix for the prompt")
async def set_prefix(ctx, prefix):
    ComfyHandlersContext().set_prefix(ComfyHandlersManager().get_current_handler().key(), prefix)
    await ctx.respond("```Prefix set!```")


@bot.slash_command(name="postfix", description="Set a postfix for the prompt")
async def set_postfix(ctx, postfix):
    ComfyHandlersContext().set_postfix(ComfyHandlersManager().get_current_handler().key(), postfix)
    await ctx.respond("```Postfix set!```")


@bot.slash_command(name="prefix-del", description="Remove the current prompt prefix")
async def remove_prefix(ctx):
    ComfyHandlersContext().remove_prefix(ComfyHandlersManager().get_current_handler().key())
    await ctx.respond("```Prefix removed```")


@bot.slash_command(name="postfix-del", description="Remove the current prompt postfix")
async def remove_postfix(ctx):
    ComfyHandlersContext().remove_postfix(ComfyHandlersManager().get_current_handler().key())
    await ctx.respond("```Postfix removed```")


@bot.slash_command(name="prefix-view", description="View the current prompt prefix")
async def prefix_view(ctx):
    res = ComfyHandlersContext().get_prefix(ComfyHandlersManager().get_current_handler().key())
    if res is None or len(res) == 0:
        res = "```no prefix set!```"
    await ctx.respond(res)


@bot.slash_command(name="postfix-view", description="View the current prompt postfix")
async def postfix_view(ctx):
    res = ComfyHandlersContext().get_postfix(ComfyHandlersManager().get_current_handler().key())
    if res is None or len(res) == 0:
        res = "```no postfix set!```"
    await ctx.respond(res)


@bot.slash_command(name="info", guild=discord.Object(id=1111),
                   description="information of the current workflow handler")
async def info(ctx):
    prompt_handler = ComfyHandlersManager().get_current_handler()
    await ctx.respond(prompt_handler.info())


@bot.slash_command(name="checkpoints", guild=discord.Object(id=1111), description="list of all supported checkpoints")
async def checkpoints(ctx):
    response = "Supported Checkpoints:\n\n"
    for checkpoint in ComfyClient().get_checkpoints():
        response += checkpoint + "\n\n"
    await ctx.respond(response)


async def set_handler(interaction):
    ComfyHandlersManager().set_current_handler(interaction.custom_id)
    await interaction.response.send_message("Handler [{}] selected\n\n{}".format(interaction.custom_id,
                                                                                 ComfyHandlersManager().get_current_handler().info()))


@bot.slash_command(name="handlers", guild=discord.Object(id=1111), description="list of all handlers")
async def handlers(ctx):
    view = View()
    for handler in ComfyHandlersManager().get_handlers():
        btn = Button(label=handler, style=discord.ButtonStyle.green, custom_id=handler)
        btn.callback = set_handler
        view.add_item(btn)
    await ctx.respond("Select handler:")
    await ctx.send("", view=view)


@bot.slash_command(name="q-status", guild=discord.Object(id=1113), description="Get queue status")
async def queue_status(ctx):
    response = "{}\n{}".format(ComfyClient().get_queue(), ComfyClient().get_prompt())
    await ctx.respond(response)


if __name__ == '__main__':
    token = os.getenv('DISCORD_BOT_API_TOKEN')
    os.environ['DISCORD_BOT_API_TOKEN'] = "TOKEN"
    BotDB()
    ComfyHandlersManager()
    ComfyClient()
    bot.run(token)

# class MyView(discord.ui.View):
#     @discord.ui.button(label="Button 1", row=0, style=discord.ButtonStyle.primary)
#     async def first_button_callback(self, button, interaction):
#         await interaction.response.send_message("You pressed me!")
#
#     @discord.ui.button(label="Button 2", row=1, style=discord.ButtonStyle.primary)
#     async def second_button_callback(self, button, interaction):
#         await interaction.response.send_message("You pressed me!")
