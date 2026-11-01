from django.contrib import admin
from django.http import FileResponse, JsonResponse
from django.urls import include, path
from django.conf import settings

def frontend(request):
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.exists():
        return JsonResponse({'detail': 'Uruchom frontend React lub zbuduj go zgodnie z README.'}, status=503)
    return FileResponse(index.open('rb'), content_type='text/html')

urlpatterns = [path('admin/', admin.site.urls), path('api/', include('gym.urls')), path('', frontend)]
