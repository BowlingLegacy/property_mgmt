def temp_home(request):
    active = ActiveHomepageImage.objects.first()

    # Safely get the hero image
    hero = active.active_image if active and active.active_image else None

    return render(request, "home_temp.html", {"hero": hero})

