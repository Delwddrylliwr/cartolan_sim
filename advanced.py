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
        self.buffs = game.card_type_buffs[card_type]
        
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
                    #@TODO if a buff has been doubled then it shouldn't be lost
                    setattr(token, buff_attr, getattr(self.game, buff_attr))

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
        #Randomly draw a Character card
        #@TODO let the player choose between multiple character cards
        character_cards = self.game.character_cards
        self.character_card = character_cards.pop(random.randint(0, len(character_cards)-1))
        #Take on the changes to rules based on the Character card
        self.character_card.apply_buffs(self)
        #Take on the changes to rules based on the Company card
#        self.company_card = self.game.company_cards[self.player]
#        self.company_card.apply_buffs(self)
#        #Be ready to receive further buffs from Discovery cards
#        self.discovery_cards = []
        
    def discover_card(self, card):
        '''Adds a Discovery card to the Adventurer, modifying rules according to the card's buffs
        '''
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
            #Randomly steal tiles to top up
            if isinstance(token, AdventurerAdvanced):
                if len(self.chest_tiles) < self.num_chest_tiles:
                    victim_chest = token.chest_tiles
                    self.chest_tiles.append(victim_chest.pop(random.randint(0, len(victim_chest)-1)))
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
#        if self.transfers_to_agents:
#            self.transfer_funds()
#        if self.agent_on_existing and self.check_tile_available(self.current_tile):
#            #An agent can still be placed on this existing tile, but at the cost of placing from the city
#            cost_exploring = self.game.cost_agent_exploring
#            cost_existing = self.game.cost_agent_from_city
#            if self.wealth >= cost_existing:
#                self.game.cost_agent_exploring = cost_existing
#                self.place_agent()
#                self.game.cost_agent_exploring = cost_exploring
    
    def transfer_funds(self):
        '''Offers the player the chance to move this Adventurer's trasure to any Agent.
        '''
        #@TODO need to refactor player input checks before implementing this
        return False

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