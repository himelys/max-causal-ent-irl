import numpy as np
from scipy.sparse import lil_matrix


class MDP(object):
    '''
    MDP object

    Attributes
    ----------
    self.nS : int
        Number of states in the MDP.
    self.nA : int
        Number of actions in the MDP.
    self.P : two-level dict of lists of tuples
        First key is the state and the second key is the action.
        self.P[state][action] is a list of tuples (prob, nextstate, reward).
    self.T : 3D numpy array
        The transition prob matrix of the MDP. p(s'|s,a) = self.T[s,a,s']
    '''
    def __init__(self, env=None):
        if env is not None:
            P, nS, nA, desc = MDP.env2mdp(env)
            self.env = env
            self.s = self.reset()
            self.P = P # state transition and reward probabilities, explained below
            self.nS = nS # number of states
            self.nA = nA # number of actions
            self.desc = desc # 2D array specifying what each grid cell means
            self.T = self.get_transition_matrix()


    def env2mdp(env):
        return ({s : {a : [tup[:3] for tup in tups]
                for (a, tups) in a2d.items()} for (s, a2d) in env.P.items()},
                env.nS, env.nA, env.desc)

    def get_transition_matrix(self):
        '''Return a matrix with index S,A,S' -> P(S'|S,A)'''
        T = np.zeros([self.nS, self.nA, self.nS])
        for s in range(self.nS):
            for a in range(self.nA):
                transitions = self.P[s][a]
                s_a_s = {t[1]:t[0] for t in transitions}
                for s_prime in range(self.nS):
                    if s_prime in s_a_s:
                        T[s, a, s_prime] = s_a_s[s_prime]
        return T

    def get_transition_matrix_2D(self):
        '''Return a matrix with index S,A,S' -> P(S'|S,A)'''
        T = np.zeros([self.nS * self.nA, self.nS])
        s_a_pos_index=0
        for s in range(self.nS):
            for a in range(self.nA):
                transitions = self.P[s][a]
                s_a_s = {t[1]:t[0] for t in transitions}
                for s_prime in range(self.nS):
                    if s_prime in s_a_s.keys():
                        T[s_a_pos_index, s_prime] = s_a_s[s_prime]
                s_a_pos_index+=1
        self.T_matrix = T
        self.T_matrix_transpose = T.transpose()


    def reset(self):
        self.s = 0
        return self.s

    def step(self, a, s=None):
        if s == None: s = self.s
        if len(self.P[s][a])==1:
            self.s = self.P[s][a][0][1]
            return self.s
        else:
            p_s_sa = np.asarray(self.P[s][a])[:,0]
            next_state_index = np.random.choice(len(p_s_sa), 1, p_s_sa)
            self.s = self.P[s][a][next_state_index][1]
            return self.s


class MDPOneTimeR(MDP):
    '''
    MDP object;
    One time reward: added a state with 0 reward to which the agent
    deterministically goes after collecting the reward once; always stays
    at the newly added state afterwards.)

    Attributes
    ----------
    self.nS : int
        Number of states in the MDP.
    self.nA : int
        Number of actions in the MDP.
    self.P : two-level dict of lists of tuples
        First key is the state and the second key is the action.
        self.P[state][action] is a list of tuples (prob, nextstate, reward).
    self.T : 3D numpy array
        The transition prob matrix of the MDP. p(s'|s,a) = self.T[s,a,s']
    '''
    def __init__(self, env):
        super().__init__(env)

        self.P.update({self.nS-1:{0:[(1.0,self.nS,0.0)], 1:[(1.0,self.nS,0.0)],
                                  2:[(1.0,self.nS,0.0)], 3:[(1.0,self.nS,0.0)]}})
        self.P.update({self.nS:{0:[(1.0,self.nS,0.0)], 1:[(1.0,self.nS,0.0)],
                                2:[(1.0,self.nS,0.0)], 3:[(1.0,self.nS,0.0)]}})
        self.nS += 1
        self.T = self.get_transition_matrix()


class MDP_toy_irreversibility(MDP):
    def __init__(self):

        self.nS = 4 # number of states
        self.nA = 2
        self.init_state = 0
        self.f_matrix = np.eye(self.nS)
        self.num_features=self.nS
        self.P = {}
        self.P.update({0:{0:[(1.0, 1,-.1)], 1:[(1.0, 3, 1)]}})
        self.P.update({1:{0:[(1.0, 2, 1)], 1:[(1.0, 0, 0)]}})
        self.P.update({2:{0:[(1.0, 2, 1)], 1:[(1.0, 1, -.1)]}})
        self.P.update({3:{0:[(1.0, 3, 1)], 1:[(1.0, 3, 1)]}})
        self.get_transition_matrix_2D()
        self.reset()

    def reset(self):
        self.s = 0
        return self.s


class MDP_chain(MDP):
    def __init__(self):
        self.nS = 8 # number of states
        self.nA = 3
        self.P = {}
        self.P.update({0:{0:[(1.0, 0, 1)], 1:[(1.0, 7, 1)], 2:[(1.0, 1, 1)]}})
        self.P.update({1:{0:[(1.0, 1, 1)], 1:[(1.0, 4, 1)], 2:[(1.0, 2, 1)]}})
        self.P.update({2:{0:[(1.0, 2, 1)], 1:[(1.0, 5, 1)], 2:[(1.0, 3, 1)]}})
        self.P.update({3:{0:[(1.0, 3, 1)], 1:[(1.0, 6, 1)], 2:[(1.0, 3, 1)]}})
        self.P.update({4:{0:[(1.0, 4, 1)], 1:[(1.0, 1, 1)], 2:[(1.0, 4, 1)]}})
        self.P.update({5:{0:[(1.0, 5, 1)], 1:[(1.0, 2, 1)], 2:[(1.0, 5, 1)]}})
        self.P.update({6:{0:[(1.0, 6, 1)], 1:[(1.0, 3, 1)], 2:[(1.0, 6, 1)]}})
        self.P.update({7:{0:[(1.0, 7, 1)], 1:[(1.0, 7, 1)], 2:[(1.0, 7, 1)]}})
        self.T = self.get_transition_matrix()
        self.reset()

    def reset(self):
        self.s = 0
        return self.s

class MDP_water(MDP):
    def __init__(self):
        self.nS = 7 # number of states
        self.nA = 3
        self.P = {}
        self.P.update({0:{0:[(1.0, 0, 1)], 1:[(1.0, 1, 1)], 2:[(1.0, 3, 1)]}})
        self.P.update({1:{0:[(1.0, 4, 1)], 1:[(1.0, 4, 1)], 2:[(1.0, 5, 1)]}})
        self.P.update({2:{0:[(1.0, 2, 1)], 1:[(1.0, 4, 1)], 2:[(1.0, 6, 1)]}})
        self.P.update({3:{0:[(1.0, 6, 1)], 1:[(1.0, 5, 1)], 2:[(1.0, 6, 1)]}})
        self.P.update({4:{0:[(1.0, 4, 1)], 1:[(1.0, 4, 1)], 2:[(1.0, 5, 1)]}})
        self.P.update({5:{0:[(1.0, 5, 1)], 1:[(1.0, 4, 1)], 2:[(1.0, 6, 1)]}})
        self.P.update({6:{0:[(1.0, 6, 1)], 1:[(1.0, 5, 1)], 2:[(1.0, 6, 1)]}})
        self.T = self.get_transition_matrix()
        self.reset()

    def reset(self):
        self.s = 0
        return self.s
