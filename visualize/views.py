from django.shortcuts import render, redirect, render_to_response
from django.http import HttpResponseNotFound
from django.views import View
import random
import string
import json
from .forms import InputForm, AntennaForm, ControlledConnectionsForm, AdaptiveFilteringForm
from .core import create_antenna
from .storage import cache


class InputView(View):
    def get(self, request):
        form = InputForm()
        return render(request, 'visualize/form.html', {'form': form})

    def post(self, request):
        # form = InputForm(request.POST)
        # from pdb import set_trace; set_trace()
        antenna_type = request.POST.get('antenna_type')
        return redirect('visualize:param-view', antenna_type=antenna_type)


class ParamView(View):
    def dispatch(self, *args, **kwargs):
        # from pdb import set_trace;
        # set_trace()
        if kwargs['antenna_type'] == 'controlled_connections':
            self.form = ControlledConnectionsForm
        elif kwargs['antenna_type'] == 'antenna':
            self.form = AntennaForm
        elif kwargs['antenna_type'] == 'adaptive_filtering':
            self.form = AdaptiveFilteringForm
        else:
            return render_to_response('visualize/error.html', {'errors': 'Введен несуществующий тип модели'})

        return super(ParamView, self).dispatch(*args, **kwargs)

    def get(self, request, **kwargs):
        # from pdb import set_trace; set_trace()
        context = {
            'antenna_type': self.kwargs['antenna_type'],
            'form': self.form
        }
        return render(request, 'visualize/params.html', context)

    def post(self, request, **kwargs):
        form = self.form(request.POST)
        if form.is_valid() and form.cleaned_data:
            user_key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
            cache.set(user_key, json.dumps(form.cleaned_data))
            return redirect(f'result/{user_key}')
        else:
            return render(request, 'visualize/error.html', {'errors': form.errors})


class ResultView(View):
    def get(self, request, user_key, antenna_type):

        try:
            antenna_params = json.loads(cache.get(user_key))
        except TypeError:
            return render(request, 'visualize/error.html',
                          {'errors': {antenna_type: 'Время сессии истекло'}})

        _model = create_antenna(antenna_params, antenna_type)

        context = {
            'result': _model,
            'antenna_type': antenna_type
        }

        return render(request, 'visualize/results.html', context)
