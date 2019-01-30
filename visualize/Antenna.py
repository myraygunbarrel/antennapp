import numpy as np
from numpy import pi, sin, cos, exp, dot
from abc import ABC, abstractmethod


class AbstractAntenna(ABC):
    @abstractmethod
    def __init__(self, n_array, a_apd=None, ph_apd=None,
                 d_lambda=0.6, resolution=10000, *args, **kwargs):
        self.N = int(n_array)
        self.phase_factor = d_lambda * 2 * pi
        self.theta = np.linspace(-pi / 2, pi / 2, resolution)
        self.theta_deg = np.degrees(self.theta)
        self.n = self.n_calculator(self.N)
        self.A_apd = np.ones((self.N, 1)) if a_apd is None else a_apd
        self.Fi_apd = np.zeros((self.N, 1)) if ph_apd is None else ph_apd
        self.Rez = resolution

    @staticmethod
    def value_quantizer(values, sector):
        index = [np.argmin(np.absolute(sector - value)) for value in values]
        return index

    @staticmethod
    def n_calculator(n_array):
        if n_array % 2 == 0:
            return (np.linspace(-(n_array - 1) / 2,
                                (n_array - 1) / 2, n_array)).reshape(n_array, 1)
        else:
            return (np.linspace(-np.floor(n_array / 2),
                                np.floor(n_array / 2), n_array)).reshape(n_array, 1)

    def phase_shift(self, shift, sign=1, fi_add=0.):
        return exp(1j * sign * (fi_add + self.n * sin(shift) * self.phase_factor))

    @abstractmethod
    def get_diagram(self, scan):
        pass


class Antenna(AbstractAntenna):
    def __init__(self, n_array, a_apd=None, ph_apd=None, a=1,
                 d_lambda=0.6, resolution=10000, *args, **kwargs):
        super().__init__(n_array=n_array, a_apd=a_apd, ph_apd=ph_apd, a=a,
                         d_lambda=d_lambda, resolution=resolution)
        self.Amp = a + (1 - a) * (cos(pi * self.n / (2 * self.N))) ** 2

        self.Fi_scan = None
        self.scan_ind = None

        self.element_diagram = Antenna.get_element_diagram(self)

    def get_element_diagram(self):
        return (self.Amp + self.A_apd) * self.phase_shift(shift=self.theta, fi_add=self.Fi_apd)

    def set_scan(self, fi_scan=0):
        self.Fi_scan = [np.radians(fi_scan)]
        self.scan_ind = self.value_quantizer(self.Fi_scan, self.theta)
        return self.phase_shift(sign=-1, shift=self.theta[self.scan_ind])

    def get_diagram(self, scan):
        element_diagram_scan = self.element_diagram * self.set_scan(scan)
        diagram = np.absolute(element_diagram_scan.sum(axis=0) / np.max(element_diagram_scan.sum(axis=0)))
        return diagram


class ControlledConnections(Antenna):
    def __init__(self, n_array, ph_interference, a_apd=None,
                 a_rand=None, ph_apd=None, ph_rand=None, iteration=1,
                 boresight_err=None, a=1, d_lambda=0.6,
                 resolution=10000, *args, **kwargs):
        super().__init__(n_array=n_array, a_apd=a_apd, ph_apd=ph_apd, a=a, d_lambda=d_lambda,
                         resolution=resolution)
        self.It = iteration

        ph_inter = np.radians(ph_interference)
        self.cl_index = self.value_quantizer(ph_inter, self.theta)
        self.A_rand = np.ones((self.N, 1)) if a_rand is None else a_rand
        self.Fi_rand = np.zeros((self.N, 1)) if ph_rand is None else ph_rand

        # Weights
        self.A = np.tile(self.Amp + self.A_apd + self.A_rand, (1, self.Rez))
        self.W = self.A/self.A.sum(axis=0)

        self.b_err = np.zeros(len(ph_inter), int) if boresight_err is None else \
            boresight_err
        self.element_diagram = self.get_element_diagram()

    def __repr__(self):
        return f'I\'m a Controlled Connection antenna with ' \
               f'{self.N} elements performing {self.It} iterations'

    def get_element_diagram(self):
        """
        Controlled connections algorithm
        """

        adaptive_element_diagram = Antenna.get_element_diagram(self)
        for i in range(self.It):
            element = np.zeros((self.N, self.Rez), dtype=complex)
            for r, ind in enumerate(self.cl_index):
                # первые фазовращатели
                inventor_1 = self.phase_shift(sign=-1, shift=self.theta[ind + self.b_err[r]],
                                              fi_add=(-self.Fi_apd - self.Fi_rand))
                pattern_sum = (adaptive_element_diagram * inventor_1).sum(axis=0)

                # вторые фазовращатели
                inventor_2 = self.phase_shift(shift=self.theta[ind + self.b_err[r]],
                                              fi_add=(self.Fi_apd + self.Fi_rand))
                element -= self.W * pattern_sum * inventor_2

            # сумматор
            adaptive_element_diagram += element

        return adaptive_element_diagram


class SubArrayControlledConnections(ControlledConnections):
    def __init__(self, n_array, ph_interference, a_apd=None,
                 a_rand=None, ph_apd=None, ph_rand=None, iteration=1,
                 boresight_err=None, sub_array=1, a=1, d_lambda=0.6,
                 resolution=10000, *args, **kwargs):
        super().__init__(n_array=n_array, ph_interference=ph_interference, a_apd=a_apd,
                         a_rand=a_rand, ph_apd=ph_apd, ph_rand=ph_rand, iteration=iteration,
                         boresight_err=boresight_err, a=a, d_lambda=d_lambda, resolution=resolution)
        self.sub_array = int(sub_array)
        # количество излучателей в одной подрешетке
        self.N_sub_array = int(self.N/self.sub_array)
        self.element_diagram = self.get_element_diagram()

    def __str__(self):
        return f'I\'m a Controlled Connection antenna with ' \
               f'{self.N} elements and {self.sub_array} sub arrays ' \
               f'performing {self.It} iterations'

    def get_element_diagram(self):
        for i in range(self.It):

            element = np.zeros((self.N, self.Rez), dtype=complex)
            j = 0
            for knife in range(self.sub_array):  # Subarray ripping

                for r, ind in enumerate(self.cl_index):
                    # первые фазовращатели
                    inventor_1 = exp(
                        -1j * (self.n[j:j + self.N_sub_array, :] *
                               sin(self.theta[ind + self.b_err[r]]) *
                               self.phase_factor - self.Fi_apd[j:j + self.N_sub_array, :] -
                               self.Fi_rand[j:j + self.N_sub_array, :]))
                    pattern_sum = ((self.element_diagram[j:j + self.N_sub_array, :] *
                                    inventor_1).sum(axis=0).reshape(self.Rez, 1)).T

                    # вторые фазовращатели
                    inventor_2 = exp(
                        1j * (self.n[j:j + self.N_sub_array, :] *
                              sin(self.theta[ind + self.b_err[r]]) *
                              self.phase_factor + self.Fi_apd[j:j + self.N_sub_array, :] +
                              self.Fi_rand[j:j + self.N_sub_array, :]))
                    element[j:j + self.N_sub_array, :] = element[j:j + self.N_sub_array, :] - \
                                                         self.W[j:j + self.N_sub_array, :] * \
                                                         pattern_sum * inventor_2

                # сумматор
                self.element_diagram[j:j + self.N_sub_array, :] = self.element_diagram[j:j + self.N_sub_array, :] + \
                                                                  element[j:j + self.N_sub_array, :]
                j += self.N_sub_array
        return self.element_diagram


class AdaptiveAntenna(AbstractAntenna):
    def __init__(self, n_array, ph_interference, sample_size=200, a_apd=None,
                 ph_apd=None, d_lambda=0.6, clatter=None, random_state=42,
                 SNR_db=20, resolution=10000, *args, **kwargs):
        super().__init__(n_array=n_array, d_lambda=d_lambda, resolution=resolution,
                         a_apd=a_apd, ph_apd=ph_apd)
        self.sample_size = sample_size

        self.Fi_scan = None
        self.scan_ind = None

        ph_inter = np.radians(ph_interference)
        self.cl_index = self.value_quantizer(ph_inter, self.theta)
        self.amount = len(self.cl_index)
        self.ph = np.linspace(-10 * pi, 10 * pi, self.sample_size)
        self.SNR = SNR_db
        self.clatter_ratio = None
        self.random_state = random_state
        self.interferences = np.zeros((self.sample_size, self.amount), complex)
        self.clatter = clatter or self.clatter_generator()

    def __repr__(self):
        return f'{self.__class__.__name__} with {self.N} elements and {self.sample_size} samples'

    def clatter_generator(self, clatter_ratio=None, clatter=None):
        np.random.seed(self.random_state)
        self.clatter_ratio = clatter_ratio

        clatter_power = 10**(self.SNR/20)

        c_r = np.array(self.clatter_ratio) * clatter_power if self.clatter_ratio \
            else [clatter_power / self.amount]*self.amount
        clatter_type = ['harmonic', 'noise', 'pulse']
        clatter_ind = np.random.randint(0, len(clatter_type), size=self.amount)
        clatter_matrix = np.zeros((self.sample_size, self.N), complex)

        for i, ind in enumerate(clatter_ind):

            if clatter_type[ind] == 'pulse':
                clatter = c_r[i] * \
                           sin(np.random.normal(0, 2, size=self.amount)[i] * self.ph).reshape(self.sample_size, 1) * \
                           exp(-1j * (self.n.T * self.phase_factor * sin(self.theta[self.cl_index[i]])))
                boarder = np.random.randint(0, 15, size=2 * self.amount)
                clatter[((self.ph > -boarder[i]) & (self.ph < boarder[-i]))] = 0

            if clatter_type[ind] == 'noise':
                clatter = np.random.normal(0, c_r[i], size=(self.sample_size, 1)) * \
                          exp(-1j * (self.n.T * self.phase_factor * sin(self.theta[self.cl_index[i]])))

            if clatter_type[ind] == 'harmonic':
                clatter = c_r[i] * sin(np.random.normal(0, 1.5, size=self.amount)[i] *
                                       self.ph).reshape(self.sample_size, 1) * \
                           exp(-1j * (self.n.T * self.phase_factor * sin(self.theta[self.cl_index[i]])))
            clatter_matrix += clatter
            self.interferences[:, i] = clatter[:, self.N // 2]

        return (clatter_matrix + np.random.normal(0, 1, size=(self.sample_size, self.N))) * \
            exp(-1j * self.Fi_apd.T) + self.A_apd.T

    def get_diagram(self, scan):

        self.Fi_scan = [np.radians(scan)]
        self.scan_ind = self.value_quantizer(self.Fi_scan, self.theta)

        S = self.phase_shift(sign=-1, shift=self.theta[self.scan_ind])
        R = (1 / 2) * dot(self.clatter.T, np.conj(self.clatter))
        W = np.linalg.solve(R, S)

        pattern = (W * exp(1j * self.phase_factor * dot(self.n, sin(self.theta.reshape(1, self.Rez))))).sum(axis=0)

        return np.absolute(pattern/max(pattern))

