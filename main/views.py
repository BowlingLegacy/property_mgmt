from django.http import HttpResponse

def home(request):
    return HttpResponse("Painted Lady Inn — Online and Running")
