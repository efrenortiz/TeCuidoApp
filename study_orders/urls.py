from django.urls import path

from study_orders import api

app_name = "study_orders_api"

urlpatterns = [
    path("study-orders/", api.StudyOrderListCreateView.as_view(), name="study_order_list_create"),
    path("study-orders/<int:pk>/", api.StudyOrderDetailView.as_view(), name="study_order_detail"),
    path("study-orders/<int:pk>/versions/", api.StudyOrderVersionsView.as_view(), name="study_order_versions"),
    path("study-orders/<int:pk>/void/", api.StudyOrderVoidView.as_view(), name="study_order_void"),
]
