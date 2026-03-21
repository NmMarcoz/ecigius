import numpy as np

def ecg_derivatives_dynamic(t, state, omega_func, params, z0_func):
    """Calcula as derivadas do sistema para um dado instante t."""
    x, y, z = state
    
    alpha = 1.0 - np.sqrt(x**2 + y**2)
    omega = omega_func(t) 
    theta = np.arctan2(y, x)
    
    dx_dt = alpha * x - omega * y
    dy_dt = alpha * y + omega * x
    
    dtheta = (theta - params['theta_i']) % (2 * np.pi)
    dtheta[dtheta > np.pi] -= 2 * np.pi
    
    z_sum = np.sum(params['a_i'] * dtheta * np.exp(-0.5 * (dtheta / params['b_i'])**2))
    dz_dt = -z_sum - (z - z0_func(t))
    
    return [dx_dt, dy_dt, dz_dt]