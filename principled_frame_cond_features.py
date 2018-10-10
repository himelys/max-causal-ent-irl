import numpy as np
from scipy.stats import norm, laplace
from scipy.optimize import check_grad

from value_iter import value_iter
from envs.utils import unique_perm, zeros_with_ones, printoptions


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
    D, d_last_step_list = p_0, [p_0]
    for t in range(T-1):
        # D(s') = \sum_{s, a} D_prev(s) * p(a | s) * p(s' | s, a)
        state_action_prob = np.expand_dims(D, axis=1) * policy[t]
        D = mdp.T_matrix_transpose.dot(state_action_prob.flatten())

        if verbose is True: print(D)
        if return_all: d_last_step_list.append(D)

    return (D, d_last_step_list) if return_all else D


def compute_g_deterministic(mdp, policy, p_0, T, d_last_step_list, feature_matrix):
    # base case
    G = np.expand_dims(p_0, axis=1) * feature_matrix

    # recursive case
    for t in range(T-1):
        # G(s') = \sum_{s, a} p(a | s) p(s' | s, a) [ d_last_step_list[t] feature_matrix[s'] + G_prev[s] ]
        # Distribute the addition to get two different terms
        G_first = np.expand_dims(d_last_step_list[t], axis=1) * policy[t]
        G_first = G_first.reshape((mdp.nS * mdp.nA,))
        G_first = mdp.T_matrix_transpose.dot(G_first)
        G_first = np.expand_dims(G_first, axis=1) * feature_matrix

        G_second = np.expand_dims(policy[t], axis=-1) * np.expand_dims(G, axis=1)
        G_second = G_second.reshape((mdp.nS * mdp.nA, mdp.num_features))
        G_second = mdp.T_matrix_transpose.dot(G_second)

        G = G_first + G_second

    return G


def om_method(mdp, s_current, p_0, horizon, temp=1, epochs=1, learning_rate=0.2, r_prior=None, r_vec=None, threshold=1e-3, check_grad_flag=False):
    '''Modified MaxCausalEnt that maximizes last step occupancy measure for the current state'''

    def compute_grad(r_vec):
        # Compute the Boltzmann rational policy \pi_{s,a} = \exp(Q_{s,a} - V_s)
        policy = value_iter(mdp, 1, mdp.f_matrix @ r_vec, horizon, temp)

        d_last_step, d_last_step_list = compute_d_last_step(
            mdp, policy, p_0, horizon, return_all=True)
        if d_last_step[s_current] == 0:
            print('Error in om_method: No feasible trajectories!')
            return r_vec

        feature_expectations = sum(d_last_step_list) @ mdp.f_matrix

        G = compute_g_deterministic(
            mdp, policy, p_0, horizon, d_last_step_list, mdp.f_matrix)
        # Compute the gradient
        dL_dr_vec = G[s_current] / d_last_step[s_current] - feature_expectations
        # Gradient of the prior
        if r_prior!= None: dL_dr_vec += r_prior.logdistr_grad(r_vec)

        return dL_dr_vec

    def compute_log_likelihood(r_vec):
        policy = value_iter(mdp, 1, mdp.f_matrix @ r_vec, horizon, temp)

        d_last_step, d_last_step_list = compute_d_last_step(
            mdp, policy, p_0, horizon, return_all=True)

        log_likelihood = np.log(d_last_step[s_current])
        if r_prior!= None: log_likelihood += np.sum(r_prior.logpdf(r_vec))

        return log_likelihood

    if r_vec is None:
        r_vec = 0.01*np.random.randn(mdp.f_matrix.shape[1])
    print('Initial reward vector: {}'.format(r_vec))

    if check_grad_flag: grad_error_list=[]

    for i in range(epochs):
        if check_grad_flag:
            grad_error_list.append(check_grad(compute_log_likelihood, compute_grad, r_vec))

        # Gradient ascent
        dL_dr_vec = compute_grad(r_vec)
        r_vec = r_vec + learning_rate * dL_dr_vec

        if i%1==0:
            with printoptions(precision=4, suppress=True):
                print('Epoch {}; Reward vector: {}'.format(i, r_vec))
                if check_grad_flag: print('grad error: {}'.format(grad_error_list[-1]))

        if np.linalg.norm(dL_dr_vec) < threshold:
            if check_grad_flag:
                print()
                print('Max grad error: {}'.format(np.amax(np.asarray(grad_error_list))))
                print('Median grad error: {}'.format(np.median(np.asarray(grad_error_list))))
            break

    return r_vec
