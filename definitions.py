import numpy as np
import re

# Factor for converting a sigma to a FWHM and back
FWHM_factor = 2 * np.sqrt(2 * np.log(2))

detector_pixel_size = 10e-6 # m

# Detector size
detector_size = 11e-3 # m

# Number of pixels
detector_pixels = 1001

# Pixel size
detector_pixel_size = detector_size / detector_pixels

# Detector sampling rate
f_s = 1/detector_pixel_size # m-1

# Sample volume thickness
t = 0.001 # m
# Radius of sphere, equal to 1 um but expressed in AA
R = 10000e-10 # m
# Volume ratio
phi = 0.015
delta_rho = 1.8e10 * (1e2) ** 2 # 1/m^2 (?)

c = 4.63e14 # T-1 m-2
theta_0 = np.deg2rad(5.5) # rad
wavelength = 2.165e-10 # m
L_s = 1.8 # m

B_s = 1
d = 3e-6
def tune_foil(lambda_0, n = 0):
    return np.arcsin(c * d * B_s * lambda_0 / ((2 * n + 1) * np.pi))

def s_t(R = R, t = t, wavelength = wavelength, phi=phi, delta_rho=delta_rho):
    return 3/2 * phi * (1 - phi) * delta_rho**2 * wavelength**2 * t * R


def compute_p_0(By, wavelength, theta_0):
    delta_B = By
    p_0 = np.pi * np.tan(theta_0) / (c * wavelength * delta_B)
    return p_0

# Computes the z corresponding to a certain By given other fixed parameters
def compute_z(By, theta_0 = theta_0, wavelength=wavelength, L_s = L_s):
    # B_2 - B_1 generally
    delta_B = By
    # Distance from detector to sample
    z = c * wavelength ** 2 * delta_B * L_s / (np.pi * np.tan(theta_0))
    return z

# Computes By given z and other fixed parameters
def compute_By(z, L_s = L_s):
    # Distance from detector to sample
    delta_B = np.pi * np.tan(theta_0) * z / (c * wavelength ** 2 * L_s)
    return delta_B


def G_0(xi):
    res = np.zeros_like(xi)
    res[xi>=2.0] = 0
    valid_xi = xi[xi<2.0]
    res[xi<2.0] = np.sqrt(1 - (valid_xi / 2) ** 2) * (1 + valid_xi ** 2 / 8)\
         + 1 / 2 * valid_xi ** 2 * (1 - (valid_xi / 4 ) ** 2) * np.log(valid_xi / (2 + np.sqrt(4 - valid_xi ** 2)))
    return res

def G(z, R):
    xi = z/R
    return s_t(R) * G_0(xi)

def form_factor(Q, R):
    return (3 * (np.sin(Q * R) - Q * R * np.cos(Q * R))/ (Q * R) ** 3)**2

def P_analytical(z, R, t, wavelength):
    xi = z/R
    return np.exp(s_t(R,t,wavelength) * (G_0(xi) - 1))

def G_norm(z, R):
    xi = z/R
    return G_0(xi)

def compute_P_dark_field(I_up,I_down):
    return  (I_up - I_down) / (I_up + I_down)


# Data processing helper functions
def extract_parameters(file):
    parameters = {}
    pattern = re.compile(r'# Param:\s*(\w+)=([\d\.]+)')
    with open(file, 'r') as file:
        for line in file:
            match = pattern.search(line)
            if match:
                param_name = match.group(1)
                param_value = float(match.group(2))
                parameters[param_name] = param_value
    return parameters

def get_data(i, folder='data'):
    y, I_up = np.genfromtxt(f'{folder}/up/{i}/det.dat', delimiter=' ', usecols=(0,1), unpack=True)
    _, I_down = np.genfromtxt(f'{folder}/down/{i}/det.dat', delimiter=' ', usecols=(0,1), unpack=True)
    _, I_empty_up = np.genfromtxt(f'{folder}/empty_up/{i}/det.dat', delimiter=' ', usecols=(0,1), unpack=True)
    _, I_empty_down = np.genfromtxt(f'{folder}/empty_down/{i}/det.dat', delimiter=' ', usecols=(0,1), unpack=True)
    parameters = extract_parameters(f'{folder}/up/{i}/det.dat')
    By = parameters['By']
    return y, I_up, I_down, I_empty_up, I_empty_down, By

def indices_within_range(x, a, b):
    return np.where((x >= a) & (x <= b))[0]

def alpha_fun(delta_B, theta_0):
    return c * delta_B / (np.pi * np.tan(theta_0))

def I_envelope(y, delta_B, theta_0, wl_sigma):
    alpha = alpha_fun(delta_B, theta_0)
    E_y = np.exp(-0.5 * (2 * np.pi * alpha * wl_sigma * y) ** 2)
    return E_y
def I_empty_analytical(y, lambda_0, delta_B, theta_0, wl_sigma, up = True):
    E_y = I_envelope(y, delta_B, theta_0, wl_sigma)
    alpha = alpha_fun(delta_B, theta_0)
    # mod = np.cos(2 * np.pi * alpha * lambda_0 * y)
    p_0 = compute_p_0(delta_B, lambda_0, theta_0)
    # print(p_0)
    mod = np.cos(2 * np.pi * lambda_0 * alpha * y)
    # print(alpha * lambda_0 * y)
    # print(mod)
    if up:
        return mod * E_y
    else:
        return -mod * E_y