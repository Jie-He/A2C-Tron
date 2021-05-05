import os
from os import listdir
from os.path import isfile, join
import os.path as path
import numpy as np
import random
from collections import namedtuple

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.distributions import Categorical

import settings as s
from Players.Player import Player

Transition = namedtuple('Transition',
                        ('state', 'action', 'next_state', 'reward', 'is_final'))

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

STATE_SIZE = 3 * s.MAP_SIZE * s.MAP_SIZE

DIR = os.path.join(os.path.dirname(os.path.join( os.path.dirname( __file__ ))), 'models')
EXT = '.hdd'

def t(x): return torch.tensor(x, device=device).float()

## Our code
class ActorAdv(nn.Module):
    def __init__(self, state_dim, n_actions):
        super().__init__()
        self.state_dim = state_dim
        self.model = nn.Sequential(
            nn.Linear(state_dim, 1024),
            nn.Tanh(),
            nn.Linear(1024, 512),
            nn.Tanh(),
            nn.Linear(512, n_actions),
        )

        self.views = nn.Sequential(
            nn.Linear(9, 64),
            nn.Tanh(),
            nn.Linear(64, n_actions),
        )

        self.mergeValue = nn.Sequential(
            nn.Linear(8, 128),
            nn.Tanh(),
            nn.Linear(128, 1),
        )

        self.mergeAdv = nn.Sequential(
            nn.Linear(8, 128),
            nn.Tanh(),
            nn.Linear(128, n_actions),
        )
    
    def forward(self, state):
        # X, V = torch.flatten(t(state[0])), torch.flatten(t(state[1]))
        X = state[:, 0:self.state_dim]
        V = state[:, self.state_dim: ]

        overview = self.model(X)
        navigate = self.views(V)

        combined = torch.cat([overview, navigate], dim=1)
        advantage = self.mergeAdv(combined)
        return self.mergeValue(combined) + advantage - advantage.mean()

## ReplayMem class from 
## https://pytorch.org/tutorials/intermediate/reinforcement_q_learning.html
class ReplayMem(object):
    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = []
        self.position = 0

    def push(self, *args):
        if len(self.memory) < self.capacity:
            self.memory.append(None)
        self.memory[self.position] = Transition(*args)
        self.position = (self.position + 1) % self.capacity

    def sample(self, n_batch):
        return random.sample(self.memory, n_batch)

    def __len__(self):
        return len(self.memory)

class DQNPlayer(Player):
    def __init__(self, model_name='DQN_Player', savef=1000, epsdecay=0.99995):
        super(DQNPlayer, self).__init__()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print("running on", self.device)
        self.epoch = 0
        self.model_name = model_name
        self.target_update = 10
        # models
        self.policy_net = ActorAdv(STATE_SIZE, 4).to(self.device)
        # optimisers
        self.optimiser = optim.Adam(self.policy_net.parameters(), lr=0.00001)
        self.target_net = ActorAdv(STATE_SIZE, 4).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.memory = ReplayMem(10000)

        self.epsilon = 0.9
        print('DECAY', epsdecay)
        self.decay   = epsdecay

        self.acc_reward = 0
        self.SFQ = savef
        self.load_weights()
    
    ## Our code
    def load_weights(self):
        print('Trying')
        ffolder = path.join(DIR, self.model_name)
        if not os.path.exists(ffolder):
            os.makedirs(ffolder)
            print('No folder!')
            return

        cpoints = [f for f in listdir(ffolder) if isfile(join(ffolder, f))]
        cpoints.sort()

        check_point = "nothing"
        if (len(cpoints) > 0):
            print('loading', join(ffolder, cpoints[-1]))
            checkpoint = torch.load(join(ffolder, cpoints[-1]))
        else:
            print('No models found!')
            return

        self.episode_rewards = checkpoint['episode_rewards']
        self.policy_net.load_state_dict(checkpoint['model_state_dict'])
        self.optimiser.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epoch = checkpoint['epoch']
        self.epsilon = checkpoint['epsilon']
        try:
            self.decay   = checkpoint['decay']
        except: 
            print('No decay - older version')
        print('Loaded with', self.epoch, 'epochs.')
    
    ## Our code
    def save_weights(self):
        ffolder = path.join(DIR, self.model_name)
        if not os.path.exists(ffolder):
            os.makedirs(ffolder)
        epochs = len(self.episode_rewards)
        fname = path.join(ffolder, self.model_name + f"{epochs:08d}" + EXT)
        
        torch.save({
            'epoch': self.epoch,
            'model_state_dict': self.policy_net.state_dict(),
            'optimizer_state_dict': self.optimiser.state_dict(),
            'episode_rewards'   : self.episode_rewards,
            'epsilon' : self.epsilon,   
            'decay'   : self.decay,
        }, fname)
        print('Model saved.')

    # Our code
    def preprocess(self, state):
        dstate = torch.cat([t(state[0].flatten()), 
                            t(state[1].flatten())], dim=0)
        return dstate
    ## Our code
    def get_action(self, dstate):
        state = self.preprocess(dstate['net']).unsqueeze(dim=0)
        with torch.no_grad():
            pred_v = self.policy_net(state)

        a = None

        if np.random.rand() < self.epsilon:
            k = np.random.choice(np.arange(4), 1)[0]
            a = torch.tensor([k]).to(device)
        else:
            a = torch.argmax(pred_v, dim=1)
        # v = torch.gather(pred_v, dim=1, a)

        self.last_state  = state
        self.last_action = a
    
        return a.item()

    ## Our code
    def update_reward(self, dstate, reward, end_game):
        n_batch   = 128
        raw_state = self.last_state
        action    = self.last_action
        next_raw_state = dstate
        
        self.acc_reward += reward
        self.memory.push(raw_state, action,
            self.preprocess(next_raw_state), torch.tensor([reward], device=self.device), torch.tensor([end_game], device=self.device))
        if end_game:
            self.episode_rewards.append(self.acc_reward)
            self.acc_reward = 0
            self.epoch += 1
            just_updated = True
            self.epsilon *= self.decay
            if len(self.episode_rewards) % self.SFQ == 0:
                self.save_weights()
        else:
            just_updated = False
        if len(self.memory) < n_batch:
            return
        transitions = self.memory.sample(n_batch)
        # Transpose the batch (see https://stackoverflow.com/a/19343/3343043 for
        # detailed explanation). This converts batch-array of Transitions
        # to Transition of batch-arrays.
        batch = Transition(*zip(*transitions))
        state_batch = torch.cat(batch.state)

        action_batch = torch.cat(batch.action)
        reward_batch = torch.cat(batch.reward)
        non_final_mask = ~(torch.tensor(batch.is_final)) #flip is_final tensor
        non_final_next_states = [s for s, is_final in zip(batch.next_state, batch.is_final)
            if is_final == False]
        non_final_next_states = torch.stack(non_final_next_states) if len(non_final_next_states) != 0 else None
        # pass through network
        v = self.policy_net(state_batch)
        # print(v[0:10])
        # print(action_batch[0:10])
        pred_v = torch.gather(v, dim=1, index=action_batch.unsqueeze(dim=0))
        # print(pred_v.shape, pred_v[0:10])
        # calculate actual
        # use policy_net to determine next action
        next_action = self.policy_net(non_final_next_states).argmax(1).detach()
        # use target_net to predict next_next_state value
        non_final_next_v_ = self.target_net(non_final_next_states).gather(1, next_action.unsqueeze(dim=0)).squeeze()
        next_v_ = torch.zeros(n_batch, device=self.device)
        if non_final_next_states is not None:
            next_v_[non_final_mask] = non_final_next_v_.detach()
        actual_v = (next_v_ * 0.95) + reward_batch
        # Compute Huber loss
        loss = F.smooth_l1_loss(pred_v, actual_v.unsqueeze(0))
        # optimize the model
        self.optimiser.zero_grad()
        loss.backward()
        # torch.nn.utils.clip_grad_norm_(self.actor_param, self.max_g, norm_type=2) # to prevent gradient expansion, set max
        self.optimiser.step()
        # update target network if needed
        if just_updated and self.epoch % self.target_update == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())