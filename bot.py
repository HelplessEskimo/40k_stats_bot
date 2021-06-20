import discord
import random

client = discord.Client()
token = ""


def read_token():
    with open("token.txt", "r") as f:
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
        processed = process_msg(message.content[6:])
        if not processed:
            await message.channel.send("Failed to process message")
        
        output_msg = ""
        for num_dead, prob in enumerate(processed):
            output_msg += "{} dead: {:.2f}%\n".format(num_dead, prob)
        await message.channel.send(output_msg)

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
        
    if weapon_data['blast'] and target_data['number'] > 10:  # max shots
        return num_dice * dice_size
    elif weapon_data['blast'] and target_data['number'] > 5: # minimum 3 shots
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
    
    if target_data['-1 to hit']:
        to_hit += 1
    
    for i in range(num_attacks):
        if random.randint(1, 6) >= to_hit:
            num_hits += 1
            
    return num_hits


def generate_wounds(attacker_data, target_data, weapon_data, num_hits):
    """
    For the number of successful hits, roll a wound roll for each, after calculating 
    the number required to wound with the weapon.
    """
    T = target_data['T']
    
    # calculate strength of weapon if it is based on attacking model strength
    S = attacker_data['S']
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
    if S <= T/2:
        to_wound = 6
    elif S < T:
        to_wound = 5
    elif S == T:
        to_wound = 4
    elif S > T:
        to_wound = 3
    elif S >= 2*T:
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
    to_save = target_data['Sv'] + weapon_data['AP'] # AP is saved as a positive interger
    if target_data['invul'] is not None:
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
    cur_damage = 0 # wounds taken by current model taking damage
    num_dead = 0   # total number of dead models from attack sequence
    
    for i in range(num_wounds):
        if str(weapon_data['D']).isnumeric():
            cur_damage += int(weapon_data['D'])
        else:
            # damage is based on dice
            num_dice, dice_size = weapon_data['D'].split('D')
            dice_size = int(dice_size)
            if num_dice == '':
                num_dice = 1
            else:
                num_dice = int(num_dice)
            cur_damage += sum([random.randint(1, dice_size) for i in range(num_dice)])
        if cur_damage >= target_data['W']:
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
    for mod in modifiers:
        if mod[:2] == 'WS':
            modifier_dict['WS'] = int(mod[2])
        elif mod[:2] == 'BS':
            modifier_dict['BS'] = int(mod[2])
        elif mod[:2] == 'BS':
            modifier_dict['BS'] = int(mod[2])
        elif len(mod) > 3 and mod[-3:] == '+++':
            modifier_dict['FNP'] = int(mod[0])
        elif len(mod) > 2 and mod[-2:] == '++':
            modifier_dict['invul'] = int(mod[0])
        elif len(mod) == 2 and mod[1] == '+':
            modifier_dict['Sv'] = int(mod[0])
        elif mod[0] == 'S': 
            modifier_dict['S'] = mod[1:]
        elif mod[0] == 'T': 
            modifier_dict['T'] = int(mod[1:])
        elif mod[0] == 'W': 
            modifier_dict['W'] = int(mod[1:])
        elif mod[:2] == 'AP':
            modifier_dict['AP'] = int(mod[-1])
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
        
    # retrieve datasheet from dictionary created from csv
    data = {'WS': 3, 'BS': 3, 'S': 4, 'T': 4, 'W': 1, 'Sv': 4, 'invul': None, 'FNP': None, '-1 to hit': False}
    
    for mod in modifiers:
        if mod in data and modifiers[mod] is not None:
            data[mod] = modifiers[mod]
            
    print(data)
    return data

def retrieve_weapon(weapon):
    """
    Retrieve weapon stats from the dictionary containing all weapons, created from csv.
    Any modifiers to the weapon's statline provided by the user override the default values
    """
    modifiers = []
    if '[' in weapon and ']' in weapon:
        modifiers = parse_modifiers(weapon)
    
    # retrieve datasheet from dictionary created from csv
    # Strength has to be a string, due to some weapons using attacker's Strenght modified in some way
    data = {'type': "Heavy 3", 'S': '4', 'AP': 0, 'D': 1, 'blast': False, 'auto-hit': False}
    
    for mod in modifiers:
        if mod in data and modifiers[mod] is not None:
            data[mod] = modifiers[mod]
            
    print(data)
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
    except:
        print("Failed to parse message, incorrect number of arguments")
        return False
    
    num_attacks = num_attacks.strip()
    attacker_data = retrieve_datasheet(attacking_unit.strip())
    target_data = retrieve_datasheet(target_unit.strip())
    weapon_data = retrieve_weapon(weapon.strip())
    
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


def unit_dict_lookup(unit):
    found_unit = unit_dict[unit]
    return found_unit


client.run(read_token())
