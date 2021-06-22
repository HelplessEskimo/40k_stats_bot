
import discord
import random
import csv
import textdistance

info = """
####################################
Warhammer 40,000 Unit Statistics Bot
####################################
Authored by:
HelplessEskimo
Computers Are Freaky

Licensed Under GPL-2
Open Source and Free Software
"""

client = discord.Client()
token = ""


def read_token():
    with open("token.txt", "r") as f:
        token = f.read()
    return token


index_dict = {}
unit_dict = {}

wargear_index_dict = {}
wargear_dict = {}

# for autocorrect, list of unique words across all entries
faction_word_list = []
unit_word_list = []
wargear_word_list = []


@client.event
async def on_ready():
    """
    Show information on start up
    """
    create_unit_dict()
    create_wargear_dict()
    print('\nI have logged in as {0.user}'.format(client))
    print(info)


@client.event
async def on_message(message):
    """
    Main message Parser, this is messy, consider using the rewrite functions in the future.
    """
    if message.author == client.user:
        return

    if message.content.startswith('$unit'):
        processed = process_msg(message.content[6:])
        if not processed:
            await message.channel.send("Failed to process message")
            return
        output_msg = ""
        for num_dead, prob in enumerate(processed):
            output_msg += "{} dead: {:.2f}%\n".format(num_dead, prob)
        await message.channel.send(output_msg)


def create_unit_dict():
    """
    Creates a dictionary entry for every unit using Wahapedia .csv files.
    Requires: Factions.csv, Datasheets.csv, Datasheets_models.csv, Datasheets_damage.csv

    The created dictionary unit_dict is organized following this format:
    {faction_id: {unit_name: {unit stats}}}

    There is a second dictionary called index_dict for matching faction names to
    faction_id. {faction_name: faction_id}
    """
    faction_data = []
    datasheet_data = []
    datasheet_model_data = []
    damage_rows = {}

    with open('Factions.csv', 'r', encoding='utf-8', newline='') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')
        for row in csv_reader:
            info = {}
            info['faction_id'], info['faction_name'], info['weblink'], _ = row
            faction_data.append(info)

        faction_data = faction_data[1:]

    with open('Datasheets.csv', 'r', encoding='utf-8', newline='') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')

        for row in csv_reader:
            info = {}
            info['datasheet_id'] = row[0]      # string: Datasheet identifier. Used to link to other tables
            info['name'] = row[1]              # string: Datasheet name
            info['link'] = row[2]              # string: Link to datasheet on the Wahapedia website
            info['faction_id'] = row[3]        # string: Faction ID (link to Factions.csv table)
            info['source_id'] = row[4]         # string: Add-on ID (link to Source.csv table)
            info['role'] = row[5]              # string: Datasheet’s Battlefield Role
            info['unit_composition'] = row[6]  # string: Unit composition and equipment
            info['transport'] = row[7]         # string: Transport capacity (if it is a TRANSPORT)
            info['power_points'] = row[8]      # string: Power Point unit cost
            info['priest'] = row[9]            # string: Description of the priest's capabilities (if it is a PRIEST)
            info['psyker'] = row[10]           # string: Description of the psykers's capabilities (if it is a PSYKER)
            info['open_play_only'] = row[11]   # bool:   The datasheet is intended for the Open Play game only
            info['virtual'] = row[12]          # string: Virtual datasheets not present in army list but can be summoned in some cases (eg Chaos Spawn)
            info['cost_per_unit'] = row[13]    # bool:   Cost includes all models
            info['cost'] = row[14]             # string: Unit points cost (for units without models or units with one price for all models - see cost_per_unit above)
            datasheet_data.append(info)
        datasheet_data = datasheet_data[1:]

    with open('Datasheets_models.csv', 'r', encoding='utf-8', newline='') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')

        for row in csv_reader:
            info = {}
            info['datasheet_id'] = row[0]
            info['line'] = row[1]
            info['name'] = row[2]
            info['M'] = row[3]
            info['WS'] = row[4]
            info['BS'] = row[5]
            info['S'] = row[6]
            info['T'] = row[7]
            info['W'] = row[8]
            info['A'] = row[9]
            info['Ld'] = row[10]
            info['Sv'] = row[11]
            info['cost'] = row[12]
            info['cost_description'] = row[13]
            info['models_per_unit'] = row[14]
            info['cost_including_wargear'] = row[15]
            datasheet_model_data.append(info)
        datasheet_model_data = datasheet_model_data[1:]

    with open('Datasheets_damage.csv', 'r', encoding='utf-8', newline='') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')

        for row in csv_reader:
            if row[0] not in damage_rows:
                damage_rows[row[0]] = [row[1:]]
            else:
                damage_rows[row[0]].append(row[1:])

    for faction in faction_data:
        index_dict["{}".format(faction['faction_name'])] = faction['faction_id']

    for faction_id in index_dict:
        unit_dict[index_dict[faction_id]] = {}

    for datasheet in datasheet_data:
        for datasheet_stats in datasheet_model_data:
            if datasheet['datasheet_id'] == datasheet_stats['datasheet_id']:
                unit_dict[datasheet["faction_id"]][datasheet["name"]] = datasheet_stats

                # for multiwound models, this replaces the variable entries with their top profile stats
                if datasheet['datasheet_id'] in damage_rows:
                    for i, stat in enumerate(damage_rows[datasheet['datasheet_id']][0][2:]):
                        if stat != '':
                            unit_dict[datasheet["faction_id"]][datasheet["name"]][stat] = damage_rows[datasheet['datasheet_id']][1][i + 2]

    global faction_word_list
    global unit_word_list

    faction_word_list = list(set(sum([i.split() for i in index_dict.keys()], [])))
    for faction in unit_dict:
        unit_word_list += sum([i.split() for i in unit_dict[faction].keys()], [])
    unit_word_list = list(set(unit_word_list))


def create_wargear_dict():
    """
    Creates a dictionary entry for every Weapon using Wahapedia .csv files.
    Requires: Wargear.csv, Wargear_list.csv

    The created dictionary unit_dict is organised following this format:
    {weapon_id: {"weapon_name": xxx, "stats": [{"name": profile 1 name,  stats...}]}}

    The list contains an entry with all stats for each weeapon profile, along with the name of that profile

    There is a second dictionary called wargear_index_dict for matching weapon names to
    weapon_id. {weapon_name: weapon_id}
    """
    with open('Wargear.csv', 'r', encoding='utf-8', newline='') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')
        for row in csv_reader:
            if row[1] not in wargear_dict and row[1] != 'name':
                wargear_dict[row[0]] = {"name": row[1], "stats": [{}]}
                wargear_index_dict[row[1]] = row[0]

    with open('Wargear_list.csv', 'r', encoding='utf-8', newline='') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')
        for row in list(csv_reader)[1:]:
            if row[1] == '':
                continue
            while int(row[1]) > len(wargear_dict[row[0]]["stats"]):
                wargear_dict[row[0]]["stats"].append({})
            wargear_dict[row[0]]["stats"][int(row[1]) - 1]["name"] = row[2]
            wargear_dict[row[0]]["stats"][int(row[1]) - 1]["Range"] = row[3]
            wargear_dict[row[0]]["stats"][int(row[1]) - 1]["type"] = row[4]
            wargear_dict[row[0]]["stats"][int(row[1]) - 1]["S"] = row[5]
            wargear_dict[row[0]]["stats"][int(row[1]) - 1]["AP"] = row[6]
            wargear_dict[row[0]]["stats"][int(row[1]) - 1]["D"] = row[7]
            wargear_dict[row[0]]["stats"][int(row[1]) - 1]["blast"] = ('Blast' in row[8])
            wargear_dict[row[0]]["stats"][int(row[1]) - 1]["auto-hit"] = ('automatically hits' in row[8])

    global wargear_word_list
    wargear_word_list = list(set(sum([i.split() for i in wargear_index_dict.keys()], [])))


def autocorrect(word, word_list):
    if word in word_list:
        return word
    else:
        similarities = [(v, 1 - (textdistance.Jaccard(qval=2).distance(v, word))) for v in word_list]
        similarities.sort(key=lambda tup: tup[1], reverse=True)

    return similarities[0][0]


def generate_attacks(num_attacks, target_data, weapon_data):
    """
    Calculate the number of attacks. Takes into account shotcount based on dice
    and factors in blast if the squad size is specified and relevant.
    """
    if num_attacks.isnumeric():
        return int(num_attacks)

    num_dice, dice_size = num_attacks.split('D')
    dice_size = int(dice_size)
    if num_dice == '':
        num_dice = 1
    else:
        num_dice = int(num_dice)

    if weapon_data['blast'] and target_data['number'] > 10:   # max shots
        return num_dice * dice_size
    elif weapon_data['blast'] and target_data['number'] > 5:  # minimum 3 shots
        return max(sum([random.randint(1, dice_size) for i in range(num_dice)]), 3)
    return sum([random.randint(1, dice_size) for i in range(num_dice)])


def generate_hits(attacker_data, target_data, weapon_data, num_attacks):
    """
    Roll a hit roll for each attack.
    """
    # In the even the weapon auto-hits, e.g. Flamer
    if weapon_data['auto-hit']:
        return num_attacks

    num_hits = 0

    # Use the correct BS/WS for the weapon in question
    if weapon_data['type'] == "melee":
        to_hit = attacker_data['WS']
    else:
        to_hit = attacker_data['BS']

    if to_hit[0] == '-':
        to_hit = 7
    else:
        to_hit = int(to_hit[0])

    for i in range(num_attacks):
        if random.randint(1, 6) >= to_hit:
            num_hits += 1

    return num_hits


def generate_wounds(attacker_data, target_data, weapon_data, num_hits):
    """
    For the number of successful hits, roll a wound roll for each, after calculating
    the number required to wound with the weapon.
    """
    T = int(target_data['T'])

    # calculate strength of weapon if it is based on attacking model strength
    if attacker_data['S'].isnumeric():
        S = int(attacker_data['S'])
    else:
        S = 0
    S_mod = weapon_data['S']
    if S_mod[0] == 'x':
        S *= int(S_mod[1])
    elif S_mod[0] == '+':
        S += int(S_mod[1])
    elif S_mod[0] == '-':
        S -= int(S_mod[1])
    elif S_mod.isnumeric():
        S = int(S_mod)

    # calculate number on D6 dice needed to wound
    to_wound = 0
    if S <= T / 2:
        to_wound = 6
    elif S < T:
        to_wound = 5
    elif S == T:
        to_wound = 4
    elif S > T:
        to_wound = 3
    elif S >= 2 * T:
        to_wound = 2

    num_wounds = 0
    for i in range(num_hits):
        if random.randint(1, 6) >= to_wound:
            num_wounds += 1

    return num_wounds


def generate_saves(attacker_data, target_data, weapon_data, num_wounds):
    """
    For the number of successful wounds, roll a save for each, using either Armor Save or
    Invul Save if there is one, factoring AP into the Armor Save
    """
    to_save = int(target_data['Sv'][0]) + int(weapon_data['AP'][-1])
    if 'invul' in target_data and target_data['invul'] is not None:
        to_save = min(to_save, target_data['invul'])

    num_unsaved_wounds = 0
    for i in range(num_wounds):
        if random.randint(1, 6) < to_save:
            num_unsaved_wounds += 1
    return num_unsaved_wounds


def generate_dead(attacker_data, target_data, weapon_data, num_wounds):
    """
    From the number of unsaved wounds, generate damage for each, then return the number of models
    that die as a result.
    """
    cur_damage = 0  # wounds taken by current model taking damage
    num_dead = 0    # total number of dead models from attack sequence

    if target_data['W'].isnumeric():
        target_wounds = int(target_data['W'])
    else:
        target_wounds = int(target_data['W'].split('-')[-1])

    for i in range(num_wounds):
        if str(weapon_data['D']).isnumeric():
            cur_damage += int(weapon_data['D'])
        else:
            # damage is based on dice
            num_dice, dice_size = weapon_data['D'].split('D')
            if "+" in dice_size:
                dice_size, additional_damage = dice_size.split('+')
            dice_size = int(dice_size)
            if num_dice == '':
                num_dice = 1
            else:
                num_dice = int(num_dice)
            cur_damage += sum([random.randint(1, dice_size) for i in range(num_dice)])
            if additional_damage:
                cur_damage + int(additional_damage)
        if cur_damage >= target_wounds:
            cur_damage = 0
            num_dead += 1

    # if the number of models in the target unit is specified, treat any number
    # of dead above squad size as being a squad wipe
    if target_data['number'] > 0:
        num_dead = min(num_dead, target_data['number'])

    return num_dead


def parse_modifiers(string):
    """
    Takes a string which contains modifiers provided by the user and converts these into a dictionary
    that can then be used to modify statlines.
    None = no value provided by user.
    """
    # remove everything outside of the modifiers
    temp = string.split(']')[0]
    modifiers = (temp.split('[')[-1]).split()

    # dictionary of all possible user provided modifiers
    modifier_dict = {'WS': None, 'BS': None, 'S': None, 'T': None, 'W': None, 'Sv': None, 'invul': None, 'FNP': None, 'AP': None, 'D': None}

    # process the string containing modifiers into the dictionary
    # this can probably be replaced with a "match", but I haven't updated to 3.10 yet
    # TODO: replace with match statement upon 3.10's release
    for mod in modifiers:
        if mod[:2] == 'WS':
            modifier_dict['WS'] = mod[2:]
        elif mod[:2] == 'BS':
            modifier_dict['BS'] = mod[2:]
        elif len(mod) > 3 and mod[-3:] == '+++':
            modifier_dict['FNP'] = mod
        elif len(mod) > 2 and mod[-2:] == '++':
            modifier_dict['invul'] = mod
        elif len(mod) == 2 and mod[1] == '+':
            modifier_dict['Sv'] = mod
        elif mod[0] == 'S':
            modifier_dict['S'] = mod[1:]
        elif mod[0] == 'T':
            modifier_dict['T'] = mod[1:]
        elif mod[0] == 'W':
            modifier_dict['W'] = mod[1:]
        elif mod[:2] == 'AP':
            modifier_dict['AP'] = mod[2:]
        elif mod[0] == 'D':
            modifier_dict['D'] = mod[1:]

    return modifier_dict


def retrieve_datasheet(unit):
    """
    Retrieve a datasheet statline from the dictionary containing all datasheets, created from csv.
    Any modifiers to the statline provided by the user override the default values
    """
    modifiers = []
    if '[' in unit and ']' in unit:
        modifiers = parse_modifiers(unit)

    unit_string = unit.split(']')[-1]
    unit_words = unit_string.split()

    faction_keyword = None
    unit_name = None

    corrected_faction_words = [autocorrect(i, faction_word_list) for i in unit_words]
    print(corrected_faction_words)
    for i in range(len(corrected_faction_words)):
        if ' '.join(corrected_faction_words[:(i + 1)]) in index_dict:
            faction_keyword = index_dict[' '.join(corrected_faction_words[:(i + 1)])]
    if faction_keyword is None:
        print("Could not identify Faction")
        return False

    corrected_unit_words = [autocorrect(i, unit_word_list) for i in unit_words]
    for i in range(len(corrected_unit_words)):
        if ' '.join(corrected_unit_words[-(i + 1):]) in unit_dict[faction_keyword]:
            unit_name = ' '.join(corrected_unit_words[-(i + 1):])
    if unit_name is None:
        print("Could not identify Unit Name")
        return False

    data = unit_dict[faction_keyword][unit_name].copy()

    for mod in modifiers:
        if mod in data and modifiers[mod] is not None:
            data[mod] = modifiers[mod]

    return data


def retrieve_weapon(weapon):
    """
    Retrieve weapon stats from the dictionary containing all weapons, created from csv.
    Any modifiers to the weapon's statline provided by the user override the default values
    """
    modifiers = []
    if '[' in weapon and ']' in weapon:
        modifiers = parse_modifiers(weapon)

    weapon_string = weapon.split(']')[-1]
    weapon_words = weapon_string.split()

    weapon_id = None

    corrected_weapon_words = [autocorrect(i, wargear_word_list) for i in weapon_words]
    for i in range(len(corrected_weapon_words)):
        if ' '.join(corrected_weapon_words[:(i + 1)]) in wargear_index_dict:
            weapon_id = wargear_index_dict[' '.join(corrected_weapon_words[:(i + 1)])]
    if weapon_id is None:
        print("Could not identify weapon")
        return False

    data = wargear_dict[weapon_id]["stats"][0].copy()

    for mod in modifiers:
        if mod in data and modifiers[mod] is not None:
            data[mod] = modifiers[mod]

    return data


def process_msg(msg):
    """
    Separates and processes each part of the request to create a distribution for dead models.
    This distribution depends on the datasheet data for the attacking model, the targeted model
    and the weapon being used. Stats can be modified in the request, e.g. ""[WS2+ S5] Space Marine Intercessor"
    The format for requests:
    number of attacks, [modifiers] attacking model name, [modifiers] weapon, target unit size (optional), [modifiers] targeted unit

    If not providing target unit size, it uses worse case scenario (e.g. 5 or less for blast weapons). If it is not provided,
    do not include the comma for it.
    """
    if msg == "":
        return False

    try:
        num_target = 0
        split_msg = msg.split(',')

        # assume target unit size was not included
        if len(split_msg) == 4:
            num_attacks, attacking_unit, weapon, target_unit = split_msg
        elif len(split_msg) == 5:
            num_attacks, attacking_unit, weapon, num_target_unit, target_unit = split_msg
            num_target = int(num_target_unit.strip())
    except all:
        print("Failed to parse message, incorrect number of arguments")
        return False

    num_attacks = num_attacks.strip()
    attacker_data = retrieve_datasheet(attacking_unit.strip())
    target_data = retrieve_datasheet(target_unit.strip())
    weapon_data = retrieve_weapon(weapon.strip())

    if not attacker_data:
        return False
    if not target_data:
        return False
    if not weapon_data:
        return False

    target_data['number'] = num_target

    # prepare array to store number of dead target models for each generated attack sequence
    # index is number of dead models, value contained is the number of times this happened
    dead = [0]

    # generate a large number of attacks sequences to estimate average distribution through Montecarlo
    num_trials = 50000
    for i in range(num_trials):
        num_attack = generate_attacks(str(num_attacks), target_data, weapon_data)
        num_hits = generate_hits(attacker_data, target_data, weapon_data, num_attack)
        num_wounds = generate_wounds(attacker_data, target_data, weapon_data, num_hits)
        num_unsaved_wounds = generate_saves(attacker_data, target_data, weapon_data, num_wounds)
        num_dead = generate_dead(attacker_data, target_data, weapon_data, num_unsaved_wounds)

        # lengthen the array as needed to store number of times n models died.
        if num_dead + 1 > len(dead):
            temp_dead = [0] * (num_dead + 1)
            temp_dead[:len(dead)] = dead[:]
            dead = temp_dead

        dead[num_dead] += 1

    # convert results of Montecarlo into %
    for i in range(len(dead)):
        dead[i] /= num_trials
        dead[i] *= 100
    return dead


client.run(read_token())
