from django.urls import path
from . import views

app_name = 'visualize'
urlpatterns = [
    path('', views.InputView.as_view(), name='input-view'),
    path('<antenna_type>/', views.ParamView.as_view(), name='param-view'),
    path('<antenna_type>/result/', views.ResultView.as_view(), name='result-view')
]
