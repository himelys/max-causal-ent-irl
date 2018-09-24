import numpy as np
from value_iter_and_policy import softmax

def value_iter(mdp, gamma, r, horizon, temperature=1, threshold=1e-10):
        '''
        Finds the optimal state and state-action value functions via value
        iteration with the "soft" max-ent Bellman backup:

        Q_{sa} = r_s + gamma * \sum_{s'} p(s'|s,a)V_{s'}
        V'_s = temperature * log(\sum_a exp(Q_{sa}/temperature))

        Computes the Boltzmann rational policy
        \pi_{s,a} = exp((Q_{s,a} - V_s)/temperature).

        Parameters
        ----------
        mdp : object
            Instance of the Env class (see envs/env.py).

        gamma : float
            Discount factor; 0<=gamma<=1.
        r : 1D numpy array
            Initial reward vector with the length equal to the
            number of states in the MDP.
        horizon : int
            Horizon for the finite horizon version of value iteration.
        temperature: float
            Rationality constant to use in the value iteration equation.
        threshold : float
            Convergence threshold.

        Returns
        -------
        1D numpy array
            Array of shape (mdp.nS, 1), each V[s] is the value of state s under
            the reward r and Boltzmann policy.
        2D numpy array
            Array of shape (mdp.nS, mdp.nA), each Q[s,a] is the value of
            state-action pair [s,a] under the reward r and Boltzmann policy.
        List of 2D numpy arrays
            Arrays of shape (mdp.nS, mdp.nA), each value p[t][s,a] is the
            probability of taking action a in state s at time t.
        '''
        nS, nA = mdp.nS, mdp.nA
        # Functions for computing the policy
        expt = lambda x: np.exp(x/temperature)
        tlog = lambda x: temperature * np.log(x)

        policies = []
        V = np.copy(r)
        for _ in range(horizon):
            future_values = mdp.T_matrix.dot(V).reshape((nS, nA))
            Q = np.expand_dims(r, axis=1) + gamma * future_values

            if temperature is None:
                V = Q.max(axis=1)
                # Argmax to find the action number, then index into np.eye to
                # one hot encode. Note this will deterministically break ties
                # towards the smaller action.
                policy = np.eye(nA)[np.argmax(Q, axis=1)]
            else:
                # ∀ s: V_s = temperature * log(\sum_a exp(Q_sa/temperature))
                # ∀ s,a: policy_{s,a} = exp((Q_{s,a} - V_s)/t)
                V = softmax(Q, temperature)
                policy = expt(Q - np.expand_dims(V, axis=1))


            policies.append(policy)

            if gamma==1:
                # When \gamma=1, the backup operator is equivariant under adding
                # a constant to all entries of V, so we can translate min(V)
                # to be 0 at each step of the softmax value iteration without
                # changing the policy it converges to, and this fixes the problem
                # where log(nA) keep getting added at each iteration.
                V = V - np.amin(V)

        return policies[::-1]
