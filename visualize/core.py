import numpy as np
from numpy import log10, round
import pandas as pd

from .image_generator import DiagramImage, ClutterImage, ScatterImage
from .Antenna import Antenna, ControlledConnections, AdaptiveAntenna


class DesignedAntenna:
    def __init__(self, antenna_params, image_required=True):
        self.scan = antenna_params.get('scan', 0)
        self.antenna_params = antenna_params
        self.generate_errors()
        self.antenna = self.create_model()
        self.diagram_in_times = self.antenna.get_diagram(self.scan)
        self.diagram = 20 * log10(self.diagram_in_times)
        if image_required:
            self.main_lobe = self.main_lobe_calc()
            if hasattr(self, 'base_antenna'):
                self.image = DiagramImage(self.antenna, self.diagram, self.base_antenna.diagram).get_image()
            else:
                self.image = DiagramImage(self.antenna, self.diagram).get_image()
            self.context = self.get_context()

    def create_model(self):
        return Antenna(**self.antenna_params)

    def get_context(self):
        context = list()
        context.append(('Количество излучателей', self.antenna.N))
        context.append(('Направление сканирования', self.scan))
        context.append(('Ширина главного лепестка Δ, °', round(self.main_lobe, 2)))
        context.append(('СКО амплитудных ошибок',  round(np.std(self.antenna.A_apd), 3)))
        context.append(('СКО фазовых ошибок, °', round(np.degrees(np.std(self.antenna.Fi_apd)), 3)))
        return context

    def generate_errors(self):
        np.random.seed(self.antenna_params.get('random_state', 42))
        a_sigma = self.antenna_params.get('a_sigma', 0)
        ph_sigma = self.antenna_params.get('ph_sigma', 0)

        N = self.antenna_params['n_array']
        self.antenna_params['a_apd'] = np.random.normal(0, a_sigma, size=(N, 1))
        self.antenna_params['ph_apd'] = np.random.normal(0, np.radians(ph_sigma), size=(N, 1))
        return N

    def main_lobe_calc(self):
        ind_3dB = self.antenna.value_quantizer([-3], self.diagram)
        main_lobe = abs(2 * (self.antenna.theta_deg[self.antenna.scan_ind[0]] - self.antenna.theta_deg[ind_3dB])[0])
        return main_lobe


class DesignedControlledConnections(DesignedAntenna):
    def __init__(self, antenna_params, image_required=True):
        self._bore_err = None
        self.base_antenna = DesignedAntenna(antenna_params, image_required=False)
        super().__init__(antenna_params=antenna_params, image_required=image_required)
        self.clutter_info = self.get_clutter_info()

    def create_model(self):
        return ControlledConnections(**self.antenna_params)

    def generate_errors(self):
        N = super().generate_errors()
        a_rand_sigma = self.antenna_params.get('a_rand', 0)
        ph_rand_sigma = self.antenna_params.get('ph_rand', 0)
        self.antenna_params['a_rand'] = np.random.normal(0, a_rand_sigma, size=(N, 1))
        self.antenna_params['ph_rand'] = np.random.normal(0, np.radians(ph_rand_sigma), size=(N, 1))

        if self.antenna_params.get('boresight_err'):
            self.antenna_params['boresight_err'] = self.generate_boresight_errors(
                len(self.antenna_params.get('ph_interference')))

    def generate_boresight_errors(self, amount):
        random_sample = None
        self._bore_err = np.zeros(amount)
        angle_step = self.base_antenna.antenna.theta_deg[-2] - self.base_antenna.antenna.theta_deg[-1]

        if self.antenna_params.get('boresight_err') == 'small_err':
            random_sample = np.random.choice([-3, -2, 2, 3], amount)
            self._bore_err = angle_step * random_sample

        if self.antenna_params.get('boresight_err') == 'med_err':
            random_sample = np.random.choice([-5, -4, 4, 5], amount)
            self._bore_err = angle_step * random_sample

        if self.antenna_params.get('boresight_err') == 'large_err':
            random_sample = np.random.choice([-10, -9, -8, 8, 9, 10], amount)
            self._bore_err = angle_step * random_sample

        return random_sample

    def get_context(self):
        context = super().get_context()
        context.append(('Количество итераций', self.antenna.It))
        context.append(('СКО остаточных амплитудных ошибок',  round(np.std(self.antenna.A_rand), 3)))
        context.append(('СКО остаточных фазовых ошибок, °', round(np.degrees(np.std(self.antenna.Fi_rand)), 3)))
        return context

    def get_clutter_info(self):
        cancelling_av = round(20 * np.log10(np.mean([self.diagram_in_times[self.antenna.cl_index]])), 2)
        cancelling_av_rel = round(20 * np.log10(
            np.mean([self.diagram_in_times[self.antenna.cl_index] /
                     self.base_antenna.diagram_in_times[self.antenna.cl_index]])
        ), 2)

        clutter_info = pd.DataFrame({
            'Направление, °': [round(n, 2) for n in self.antenna.theta_deg[self.antenna.cl_index]] + ['Среднее'],
            'Подавление абсолютное, дБ': [round(n, 2) for n in self.diagram[self.antenna.cl_index]] + [cancelling_av],
            'Подавление относительное, дБ': [round(n, 2) for n in (self.diagram[self.antenna.cl_index]
                                             - self.base_antenna.diagram[self.antenna.cl_index])] + [cancelling_av_rel]
                      })

        if self._bore_err:
            bore_err = ['Δ/' + str(round(self.main_lobe / np.absolute(n), 2)) if n != 0
                        else 0 for n in self._bore_err]
            bore_err_col = pd.Series(bore_err + ['—'])
            clutter_info.loc[:, 'Ошибка пеленга'] = bore_err_col

        prepared_columns = list(clutter_info)
        prepared_values = [clutter_info.loc[row].tolist() for row in range(clutter_info.shape[0])]

        prepared_data = {
            'columns': prepared_columns,
            'parameters': prepared_values
        }

        return prepared_data


class DesignedAdaptiveFiltering(DesignedControlledConnections):
    def __init__(self, antenna_params, image_required=True):
        super().__init__(antenna_params=antenna_params, image_required=image_required)
        if self.antenna_params.get('clatter_image_required'):
            self.clutter_image = ClutterImage(self.antenna).get_image()
        if self.antenna_params.get('scatter_image_required'):
            self.scatter_image = ScatterImage(self.antenna).get_image()

    def create_model(self):
        return AdaptiveAntenna(**self.antenna_params)

    def get_context(self):
        context = DesignedAntenna.get_context(self)
        context.append(('Объем выборки', self.antenna.sample_size))
        context.append(('Отношение Помеха/Шум, дБ', self.antenna.SNR))
        return context


def create_antenna(antenna_params, antenna_type):

    factory = DesignedAntenna
    if antenna_type == 'controlled_connections':
        factory = DesignedControlledConnections
    if antenna_type == 'adaptive_filtering':
        factory = DesignedAdaptiveFiltering
    # from pdb import set_trace;
    # set_trace()
    return factory(antenna_params)

