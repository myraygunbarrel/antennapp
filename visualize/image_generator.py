from abc import ABC, abstractmethod
import pandas as pd
from pandas.plotting import scatter_matrix
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from cycler import cycler
from io import BytesIO
import base64
import warnings
warnings.filterwarnings("ignore")


matplotlib.use('Agg')

LUCKY_NUMBER = 25


def binary_saver(func):
    def wrapped(inst):
        func(inst)
        img_in_memory = BytesIO()
        inst.fig.savefig(img_in_memory, format='png', bbox_inches='tight', transparent="True", pad_inches=0)
        image = base64.b64encode(img_in_memory.getvalue()).decode()
        return image

    return wrapped


class AbstractImage(ABC):
    @abstractmethod
    def __init__(self, model):
        self._model = model
        self.fig = None

    @abstractmethod
    def get_image(self):
        pass


class DiagramImage(AbstractImage):
    def __init__(self, model, diagram, base_diagram=None):
        super().__init__(model=model)
        self._figure = diagram
        self._base_figure = base_diagram

    def base_image(self, y_min):
        x_min = -60
        x_max = -x_min
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(self._model.theta_deg, self._figure, color='#49CED4', lw=2, label='ДН адаптивной АФАР')
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, 0)
        ax.set_yticks(np.arange(y_min, 0, int(abs(y_min) / LUCKY_NUMBER)))
        ax.set_xticks(np.arange(x_min, x_max, 5))
        ax.grid(True)
        ax.set_xlabel('θ,°')
        return ax, fig

    @binary_saver
    def get_image(self):
        y_min = -LUCKY_NUMBER * 2
        if self._base_figure is not None:
            y_min = self.y_min_calc()

        ax, self.fig = self.base_image(y_min)

        if self._base_figure is not None:
            for ind in self._model.cl_index:
                ax.plot(self._model.theta_deg[ind], self._figure[ind], 'ro')
                ax.arrow(self._model.theta_deg[ind], 0, 0.0, -4, fc="k", ec="k",
                         head_width=1, head_length=3.2)

            ax.plot(self._model.theta_deg, self._base_figure, color='#9EC567',
                    ls='--', lw=1.2, label='ДН обычной АФАР')
            ax.legend(loc='lower right', fancybox=True, framealpha=0.5, fontsize='large')

    def y_min_calc(self):
        min_value = np.min(self._figure[self._model.cl_index]) - LUCKY_NUMBER
        if min_value != -float('inf'):
            y_min = LUCKY_NUMBER * (np.floor(min_value / LUCKY_NUMBER))
        else:
            y_min = -LUCKY_NUMBER * 4
        return y_min


class ClutterImage(AbstractImage):
    def __init__(self, model):
        super().__init__(model)

    @binary_saver
    def get_image(self):
        self.fig = plt.figure(figsize=(10, 7))

        amount = len(self._model.cl_index)

        for i in range(amount):
            nrows = 2 if amount <= 4 else np.ceil(amount / 2)
            ax = self.fig.add_subplot(nrows, 2, i + 1)

            ax.plot(self._model.ph, np.real(self._model.interferences[:, i]))
            ax.grid(True)


class ScatterImage(AbstractImage):
    def __init__(self, model):
        super().__init__(model)

    @binary_saver
    def get_image(self):
        self.fig = plt.figure(figsize=(8, 8))
        ax = self.fig.add_subplot(1, 1, 1)
        radiators = pd.DataFrame(np.real(self._model.clatter[:, 5:14]),
                                 columns=['-4', '-3', '-2', '-1', '0', '1', '2', '3', '4'])

        scatter_matrix(radiators, alpha=0.5, grid=True, diagonal='kde', ax=ax)



