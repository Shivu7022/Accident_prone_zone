from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health_check, name='health_check'),
    path('health/', views.health_check, name='health_check_slash'),
    
    path('risk/predict', views.predict_risk_endpoint, name='predict_risk'),
    path('risk/predict/', views.predict_risk_endpoint, name='predict_risk_slash'),
    
    path('hotspots', views.get_accident_hotspots, name='hotspots'),
    path('hotspots/', views.get_accident_hotspots, name='hotspots_slash'),
    
    path('road/<str:road_id>', views.get_road_info, name='road_info'),
    path('road/<str:road_id>/', views.get_road_info, name='road_info_slash'),
    
    path('road-damage/predict', views.calculate_damage_endpoint, name='road_damage'),
    path('road-damage/predict/', views.calculate_damage_endpoint, name='road_damage_slash'),
    
    path('traffic', views.get_traffic_endpoint, name='traffic'),
    path('traffic/', views.get_traffic_endpoint, name='traffic_slash'),
    
    path('weather', views.get_weather_endpoint, name='weather'),
    path('weather/', views.get_weather_endpoint, name='weather_slash'),
    
    path('location/search', views.search_location, name='search_location'),
    path('location/search/', views.search_location, name='search_location_slash'),
    path('location/reverse', views.reverse_geocode_endpoint, name='reverse_geocode'),
    path('location/reverse/', views.reverse_geocode_endpoint, name='reverse_geocode_slash'),
]
