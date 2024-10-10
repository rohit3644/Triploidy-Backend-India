"""
URL configuration for triploidy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from triploidy.views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('documents/', documents, name='documents'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('signup_confirm/<str:uid>/<str:token>/', signup_confirm, name='signup_confirm'),
    path('logout/', logout_view, name='logout'),
    path('upload-sample/', upload_view, name='upload_sample'),
    path('search/', search, name='search'),
    path('history/', history, name='history'),
    path('upload_media/', upload_media, name='upload_media'),
    path('password_reset/', password_reset, name='password_reset'),
    path('password_reset_confirm/<str:uid>/<str:token>/', password_reset_confirm, name='password_reset_confirm'),
    path('delete_sample_history/<str:run_id>/', delete_sample_history, name='delete_sample_history'),
    path('delete_list_ploidy/<str:id>/', delete_list_ploidy, name='delete_list_ploidy'),
    path('parental-upload-sample/', parental_upload_view, name='parental_upload_sample'),
    path('parental-history/', parental_history, name='parental_history'),
    path('killing-process/', killing_process, name='killing_process'),
    path('parental-search/', parental_search, name='parental_search'),
    path('list_ploidy/', list_ploidy, name='list_ploidy'),
    path('search_ploidy/', search_ploidy, name='search_ploidy'),
    path('upload_ploidy/', upload_ploidy, name='upload_ploidy'),
    path('parental-delete_sample_history/<str:run_id>/', parental_delete_sample_history, name='parental_delete_sample_history'),
    path('parental-ploidy-upload-sample/', parental_ploidy_upload_view, name='parental_ploidy_upload_sample'),
    path('parental-ploidy-history/', parental_ploidy_history, name='parental_ploidy_history'),
    path('parental-ploidy-search/', parental_ploidy_search, name='parental_ploidy_search'),
    path('parental-ploidy-delete_sample_history/<str:run_id>/', parental_ploidy_delete_sample_history, name='parental_ploidy_delete_sample_history'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
