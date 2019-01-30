from django import forms
from django.core.validators import RegexValidator


class InputForm(forms.Form):
    antenna_type = forms.ChoiceField(choices=(('antenna', 'Линейная АФАР'),
                                              ('controlled_connections', 'АФАР с управляемыми связями'),
                                              ('adaptive_filtering', 'АФАР с АПФ')),
                                     widget=forms.RadioSelect(), label='Выберите модель для расчёта')


class AntennaForm(forms.Form):
    n_array = forms.IntegerField(label='Количество излучателей', min_value=2, max_value=100, initial=29)
    scan = forms.FloatField(label='Направление сканирования', min_value=-45, max_value=45, initial=0.0, required=True)
    random_state = forms.IntegerField(label='Случайное состояние', min_value=0, initial=42)
    a_sigma = forms.FloatField(label='СКО амплитудных ошибок', min_value=0, max_value=1, initial=0.1, required=True)
    ph_sigma = forms.FloatField(label='СКО фазовых ошибок', min_value=0, max_value=30, initial=5, required=True)


class ControlledConnectionsForm(AntennaForm):
    ph_interference = forms.CharField(label='Направления прихода помех', min_length=1, help_text='через запятую.')
    a = forms.FloatField(label='Коэффициент а (спадающее к краям АФР)', min_value=0, max_value=1, initial=1.0,
                              required=True)
    a_rand = forms.FloatField(label='СКО остаточных амплитудных ошибок', min_value=0, max_value=1, initial=0.01,
                              required=True)
    ph_rand = forms.FloatField(label='СКО остаточных фазовых ошибок', min_value=0, max_value=30, initial=0.5,
                               required=True)
    iteration = forms.IntegerField(label='Количество итераций', min_value=1, max_value=500, initial=1)
    boresight_err = forms.ChoiceField(choices=(('no_err', 'Нет'),
                                               ('small_err', 'Малые'),
                                               ('med_err', 'Средние'),
                                               ('large_err', 'Большие')),
                                      label='Ошибки пеленга')

    def clean_ph_interference(self):
        try:
            self.cleaned_data['ph_interference'] = [float(x) for x in
                                                    set(self.cleaned_data['ph_interference'].replace(' ',
                                                                                                     '').split(','))]
            for x in self.cleaned_data['ph_interference']:
                if not (-90 <= x <= 90):
                    raise ValueError
        except ValueError:
            raise forms.ValidationError('Углы должны быть числами в диапазоне [-90.0; 90.0] '
                                        'и следовать через запятую')
        return self.cleaned_data['ph_interference']


class AdaptiveFilteringForm(ControlledConnectionsForm):
    sample_size = forms.IntegerField(label='Объем выборки', min_value=10, max_value=1000, initial=200)
    SNR_db = forms.FloatField(label='Отношение помеха / шум', min_value=0, max_value=200, initial=20,
                              required=True)
    clatter_image_required = forms.BooleanField(label='Отобразить осциллограммы помех', required=False)
    scatter_image_required = forms.BooleanField(label='Визуализировать матрицу рассеяния', required=False)
    iteration, a, a_rand, ph_rand, boresight_err = None, None, None, None, None
