from django.shortcuts import render, redirect, render_to_response
from django.http import HttpResponseNotFound
from django.views import View
from .forms import InputForm, AntennaForm, ControlledConnectionsForm, AdaptiveFilteringForm
from .core import create_antenna


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
            request.session.create()
            request.session['antenna_data'] = form.cleaned_data
            return redirect('result/')
        else:
            return render(request, 'visualize/error.html', {'errors': form.errors})


class ResultView(View):
    def get(self, request, antenna_type):

        _model = create_antenna(request.session.get('antenna_data'), antenna_type)

        context = {
            'result': _model,
            'antenna_type': antenna_type
        }
        return render(request, 'visualize/results.html', context)
