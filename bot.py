import discord

client = discord.Client()
token = ""


def read_token():
    with open("token.txt", "w") as f:
        token = f.read()
    return token


unit_dict = {
    "Primaris Lieutenant": {
        "Ws": "3+",
        "Bs": "3+",
        "Sv": "3+"
    }
}


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$unit'):
        parsed = parse_msg(message.content[6:])
        if not parsed:
            await message.channel.send("lookup failed")
        await message.channel.send(str(unit_dict_lookup(parsed[0])))


def parse_msg(msg):
    if msg == "":
        return False

    units = msg.split(",")
    return units


def unit_dict_lookup(unit):
    found_unit = unit_dict[unit]
    return found_unit


<<<<<<< HEAD
client.run(read_token())
=======
client.run('no')
>>>>>>> b67b3e363aa0a78bbf47865f5bf58a99b4488463
