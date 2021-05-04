from Players.Player import Player, BotPlayer
from Players.NetPlayer import NetPlayer
from Players.DQNPlayer import DQNPlayer
from game import Game
from Options import Options
import settings as s

from datetime import datetime
import os

OPTIONS = Options()
OPTIONS = OPTIONS.parse()

def main():
    nplayer0 = None
    if OPTIONS.model_type=='A2C':
        nplayer0 = NetPlayer(OPTIONS.model_name, savef=OPTIONS.savefreq)
    elif OPTIONS.model_type=='DQN':
        nplayer0 = DQNPlayer(OPTIONS.model_name, savef=OPTIONS.savefreq)
    else:
        print(OPTIONS.model_type + ' Model not defined!')
        exit()
#===============================================================================
    ## Training
    Game_env = Game(nplayer0, use_gui=OPTIONS.gui, depth=OPTIONS.depth, options=OPTIONS)
    epochs = 0
    k = False
    print(OPTIONS.epochs)
    while(epochs < OPTIONS.epochs):
        epochs += 1
        k = epochs % 100 == 0
        if k:
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print('[' + current_time + ']', f"{epochs:08d} ", end='')
        Game_env.reset()
        Game_env.play(k)

#===============================================================================
    ## Evaluation values
    matches = 1
    wins, draw, loss = 0, 0, 0
    ## Play 1000 games
    for m in range(matches):
        Game_env.reset()
        result = Game_env.play(True)
        print(f"{m:08d} ", end='')
        if result[0] == True:       loss += 1
        if result[1] == True:       wins += 1
        if result[0] == result[1]:  draw += 1
    assert (wins + draw + loss) == matches
    print('Results: ')
    print('Win  Rate:', "{:.2f}%".format(wins/matches*100))
    print('Draw Rate:', "{:.2f}%".format(draw/matches*100))
    print('Loss Rate:', "{:.2f}%".format(loss/matches*100))

if __name__ == "__main__":
    main()