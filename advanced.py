'''
Copyright 2020 Tom Wilkinson, delwddrylliwr@gmail.com
'''

import random
from regular import AdventurerRegular, AgentRegular, CityTileRegular
from base import WindDirection, TileEdges

class CardAdvanced():
    '''Modifies the rules for objects from other Cartolan classes.
    '''
    def __init__(self, game, card_type):
        self.game = game
        self.card_type = card_type
        self.buffs = game.card_type_buffs[card_type[3:]]
        
    def apply_buffs(self, token):
        '''Incorporates rule changes for the Adventurer/Agent that come from this cards
        '''
        for buff_attr in self.buffs:
            #Check that the token has the attribute associated with the buff
            current_attr_val = getattr(token, buff_attr, None) 
            if current_attr_val is not None:
                print("For "+token.player.colour+" player, adding a buff to their "+buff_attr)
                #Apply the buff
                if self.buffs[buff_attr]["buff_type"] == "boost":
                    setattr(token, buff_attr, current_attr_val + self.buffs[buff_attr]["buff_val"])
                elif self.buffs[buff_attr]["buff_type"] == "new":
                    setattr(token, buff_attr, self.buffs[buff_attr]["buff_val"])
                print(token.player.colour+" player's "+buff_attr+" now has value "+str(getattr(token, buff_attr, None)))
    
    def remove_buffs(self, token):
        '''Reverts rule changes for the Adventurer/Agent that come from this card
        '''
        for buff_attr in self.buffs:
            #Check that the token has the attribute associated with the buff
            current_attr_val = getattr(token, buff_attr, None) 
            if current_attr_val is not None:
                #Apply the buff
                if self.buffs[buff_attr]["buff_type"] == "boost":
                    setattr(token, buff_attr, current_attr_val - self.buffs[buff_attr]["buff_val"])
                elif self.buffs[buff_attr]["buff_type"] == "new":
                    #@TODO if a buff has been doubled up then it shouldn't be lost
                    setattr(token, buff_attr, getattr(self.game, buff_attr))
                    print(token.player.colour+" player's "+buff_attr+" now has value "+str(getattr(token, buff_attr, None)))

class AdventurerAdvanced(AdventurerRegular):
    '''Extends to allow a set of map tiles to be carried by each Adventurer in their chest and placed instead of a random one
    '''
    def __init__(self, game, player, starting_city):
        super().__init__(game, player, starting_city)
        
        #Bring in game variables that might be altered by company/character stats
        self.defence_rounds = game.defence_rounds
        self.agent_on_existing = game.agent_on_existing
        self.transfers_to_agents = game.transfers_to_agents
        self.attacks_abandon = game.attacks_abandon
        #Prepare to hold cards
        self.character_card = None
        self.discovery_cards = []
        #Randomly draw a Character card
        #let the player choose between multiple character cards if the game visual is already started
#        character_cards = self.game.character_cards
#        self.character_card = character_cards.pop(random.randint(0, len(character_cards)-1))
        if self.game.game_started:
            self.choose_character()
        #Take on the changes to rules based on the Company card
#        self.company_card = self.game.company_cards[self.player]
#        self.company_card.apply_buffs(self)
#        #Be ready to receive further buffs from Discovery cards
#        self.discovery_cards = []
    
    def choose_character(self):
        '''Lets the player choose a character card from a random subset
        '''
        character_cards = self.game.character_cards
        card_options = random.sample(character_cards, k=self.game.num_character_choices[self.player])
        self.character_card = self.player.choose_card(self, card_options)
        character_cards.remove(self.character_card)
        #Take on the changes to rules based on the Character card
        self.character_card.apply_buffs(self)
        self.replenish_chest_tiles() #in case the buffs increased the chest tile 
    
    def discover_card(self, card):
        '''Adds a Discovery card to the Adventurer, modifying rules according to the card's buffs
        '''
        print(self.player.colour+" player's Adventurer has received the card of type "+card.card_type)
        self.discovery_cards.append(card)
        card.apply_buffs(self)
    
    def attack(self, token):
        '''Extends Regular mode to allow stealing of Chest Tiles
        '''
        #If the target Adventurer has a defensive buff to force multiple rounds of attack then these need to be won first
        if isinstance(token, AdventurerAdvanced):
            for defence_round in range(0, token.defence_rounds-1):
                if random.random() > self.attack_success_prob:
                    return False
        if super().attack(token):
            if isinstance(self.current_tile, CityTileRegular): #If on a city then there's no attacking
                return True
            #Steal Discovery cards
            if isinstance(token, AdventurerAdvanced):
                if len(token.discovery_cards) > 0:
#                    stolen_card = token.discovery_cards.pop(random.randint(0, len(token.discovery_cards)-1))
                    stolen_card = self.player.choose_card(self, token.discovery_cards)
                    token.discovery_cards.remove(stolen_card)
                    self.discover_card(stolen_card)
            if self.attacks_abandon: #Adventurers will return to cities, Agents are removed
                if isinstance(token, AdventurerRegular):
                    token.end_expedition()
                elif isinstance(token, AgentRegular):
                    token.dismiss()
            return True
        else:
            return False
        
    def interact_tile(self):
        '''Extends the Regular, to allow placing Agents on existing tiles for some Adventurer buffs
        '''
        super().interact_tile()
        if self.agent_on_existing and self.check_tile_available(self.current_tile):
            #An agent can still be placed on this existing tile, but at the cost of placing from the city
            cost_exploring = self.game.cost_agent_exploring
            cost_existing = self.game.cost_agent_from_city
            if self.wealth >= cost_existing:
                self.cost_agent_exploring = cost_existing
                self.place_agent()
                self.cost_agent_exploring = cost_exploring
        if (self.transfers_to_agents 
            and len(self.game.agents[self.player]) > 0 
            and self.wealth > 0):
            #Offer the opportunity to move wealth around between Agents
            transfer_agent = self.player.check_transfer_agent(self)
            while isinstance(transfer_agent, AgentAdvanced):
                #Check the amount to transfer and move it
                transfer_amount = self.player.check_deposit(self, self.wealth, -transfer_agent.wealth)
                self.wealth -= transfer_amount
                transfer_agent.wealth += transfer_amount
                #See if another transfer is desired
                transfer_agent = self.player.check_transfer_agent(self)
    
    def interact_tokens(self):
        '''Extends regular to attack even poor Adventurers if the card is held that will send them home.
        '''
        super().interact_tokens()
        if self.current_tile.adventurers:
            for adventurer in self.current_tile.adventurers:
                if (self.attacks_abandon and adventurer.wealth == 0 
                    and not self == adventurer):
                    if self.player.check_attack_adventurer(self, adventurer):
                        self.attack(adventurer)

class AgentAdvanced(AgentRegular):
    '''Extends Regular mode to allow Agents' rules to be changed by cards
    '''
    def give_rest(self, adventurer):
        '''Extends Regular mode to replenish Chest Tiles ...now done in Regular mode
        '''
        return super().give_rest(adventurer)

class CityTileAdvanced(CityTileRegular):
    '''Extends to replenish Chest Tiles, and offer purchase of refreshed chest tiles
    '''
    def visit_city(self, adventurer, abandoned=False):
       '''Extends to allow rule changes from cards
       '''
       super().visit_city(adventurer, abandoned)
       
       if self.game.game_over or abandoned:
            return
        
       #Offer the chance to upgrade the Adventurer with a Discovery card
       available_cards = self.game.discovery_cards
       rejected_cards = []
       while (available_cards 
           and adventurer.player.vault_wealth >= self.game.cost_tech
           and adventurer.player.check_buy_tech(adventurer)):
           
           card_options = []
           #Offer several cards, but only those which don't duplicate another one time card buff the Adventurer already has
           while (len(card_options) < self.game.num_discovery_choices[adventurer.player]
               and available_cards):
               new_tech_card = available_cards.pop(random.randint(0, len(available_cards)-1))
               #Check whether this is a one off perk and then whether its a duplicate, returning it and drawing another if so
               for buff_attr in new_tech_card.buffs:
                   if new_tech_card.buffs[buff_attr]["buff_type"] == "new":
                       if buff_attr in adventurer.character_card.buffs:
                           rejected_cards.append(new_tech_card)
                           break
                       for existing_card in adventurer.discovery_cards:
                           if buff_attr in existing_card.buffs:
                               rejected_cards.append(new_tech_card)
                               break
               card_options.append(new_tech_card)
           if card_options: #Providing there were some valid discovery cards still available, let the player choose
               chosen_card = adventurer.player.choose_card(adventurer, card_options)
               card_options.remove(chosen_card)
               adventurer.discover_card(chosen_card)
               adventurer.player.vault_wealth -= self.game.cost_tech
           available_cards += card_options #Return the remaining options to the deck
           available_cards += rejected_cards #Return the cards that weren't suitable to the Discovery deck

class CapitalTileAdvanced(CityTileAdvanced):
    def __init__(self, game, tile_back = "water"
                 , wind_direction = WindDirection(True,True)
                 , tile_edges = TileEdges(True,True,True,True)):
        return super().__init__(game, wind_direction, tile_edges, True, True)

class MythicalTileAdvanced(CityTileAdvanced):
    def __init__(self, game, tile_back = "land"
                 , wind_direction = WindDirection(True,True)
                 , tile_edges = TileEdges(False,False,False,False)):
        return super().__init__(game, wind_direction, tile_edges, False, False)