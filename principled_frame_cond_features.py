import numpy as np
from scipy.stats import norm, laplace

from value_iter import value_iter
from envs.utils import unique_perm, zeros_with_ones, printoptions

def grad_gaussian_prior(theta, theta_spec, sigma=1):
    return -(theta-theta_spec)/(sigma**2)


def grad_laplace_prior(theta, theta_spec, b=1):
    return (theta_spec-theta)/(np.fabs(theta-theta_spec)*b)


class norm_distr(object):
    def __init__(self, mu, sigma=1):
        self.mu = mu
        self.sigma = sigma
        self.distribution = norm(loc=mu, scale=sigma)
        
    def rvs(self):
        '''sample'''
        return self.distribution.rvs()
    
    def pdf(self, x):
        return self.distribution.pdf(x)
    
    def logpdf(self, x):
        return self.distribution.logpdf(x)
    
    def logdistr_grad(self, x):
        return (self.mu-x)/(self.sigma**2)
    

class laplace_distr(object):
    def __init__(self, mu, b=1):
        self.mu = mu
        self.b = b
        self.distribution = laplace(loc=mu, scale=b)
        
    def rvs(self):
        '''sample'''
        return self.distribution.rvs()
    
    def pdf(self, x):
        return self.distribution.pdf(x)
    
    def logpdf(self, x):
        return self.distribution.logpdf(x)
    
    def logdistr_grad(self, x):
        return (self.mu-x)/(np.fabs(x-self.mu)*self.b)




def compute_d_last_step(mdp, policy, p_0, T, gamma=1, verbose=False, return_all=False):
    '''Computes the last-step occupancy measure'''
    D_prev = p_0
    d_last_step_list = [D_prev]

    t = 0
    for t in range(T):

        # for T-step OM we'd do D=np.copy(P_0). However, we want the last step one, so:
        D = np.zeros_like(p_0)

        # D(s') = \sum_{s, a} D_prev(s) * p(a | s) * p(s' | s, a)
        state_action_prob = np.expand_dims(D_prev, axis=1) * policy
        D = mdp.T_matrix_transpose.dot(state_action_prob.flatten())

        D_prev = np.copy(D)
        if verbose is True: print(D)
        if return_all: d_last_step_list.append(D)

    return (D, d_last_step_list) if return_all else D



def compute_g_deterministic(mdp, policy, p_0, T, d_last_step_list, feature_matrix):
    # base case
    G_prev = np.zeros((mdp.nS, feature_matrix.shape[1]))

    # recursive case
    for t in range(T-1):
        # G(s') = \sum_{s, a} p(a | s) p(s' | s, a) [ d_last_step_list[t] feature_matrix[s] + G_prev[s] ]
        tmp = np.expand_dims(d_last_step_list[t], axis=1) * feature_matrix + G_prev
        tmp = np.expand_dims(policy, axis=-1) * np.expand_dims(tmp, axis=1)
        tmp = tmp.reshape((mdp.nS * mdp.nA), mdp.num_features)
        G = mdp.T_matrix_transpose.dot(tmp)
        G_prev = np.copy(G)
    return G


def om_method(mdp, s_current, p_0, horizon, temp=1, epochs=1, learning_rate=0.2, r_prior=None, r_vec=None):
    '''Modified MaxCausalEnt that maximizes last step occupancy measure for the current state'''
    if r_vec is None:
        r_vec = .01*np.random.randn(mdp.f_matrix.shape[1])
    print('Initial reward vector: {}'.format(r_vec))

    for i in range(epochs):
        # Compute the Boltzmann rational policy \pi_{s,a} = \exp(Q_{s,a} - V_s)
        V, Q, policy = value_iter(mdp, 1, mdp.f_matrix @ r_vec, horizon, temp)

        # Compute the gradient
        d_last_step, d_last_step_list = compute_d_last_step(mdp, policy, p_0, horizon, return_all=True)
        G = compute_g_deterministic(mdp, policy, p_0, horizon, d_last_step_list, mdp.f_matrix)
        d_T_step = sum(d_last_step_list)

        g_div_d_last_step = np.zeros(mdp.f_matrix.shape[1])
        if d_last_step[s_current]!=0:
            g_div_d_last_step = G[s_current] / d_last_step[s_current]

        s_current_vec = np.zeros(env.nS)
        s_current_vec[s_current] = 1
        dL_dr_vec = g_div_d_last_step.flatten() + (s_current_vec - d_T_step) @ mdp.f_matrix

        # Gradient of the prior
        if r_prior!= None: dL_dr_vec += r_prior.logdistr_grad(r_vec)

        # Gradient ascent
        r_vec = r_vec + learning_rate * dL_dr_vec

        if i%1==0:
            with printoptions(precision=4, suppress=True):
                print('Epoch {}; Reward vector: {}'.format(i, r_vec))
    return r_vec
