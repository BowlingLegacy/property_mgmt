@login_required
@user_passes_test(staff_required)
def landlord_dashboard(request):
    applications = (
        HousingApplication.objects
        .select_related("property", "user")
        .all()
        .order_by("property__name", "space_label", "full_name")
    )

    properties = Property.objects.all().order_by("name")
    payments = Payment.objects.all().order_by("-created_at")[:25]

    resident_messages = (
        ResidentMessage.objects
        .select_related("application", "application__property")
        .all()
        .order_by("application__property__name", "-created_at")
    )

    landlord_inbox = OrderedDict()

    for resident_message in resident_messages:
        application = resident_message.application
        property_name = "No Property"

        if application and application.property:
            property_name = application.property.name

        landlord_inbox.setdefault(property_name, [])
        landlord_inbox[property_name].append(resident_message)

    new_message_count = resident_messages.filter(status="submitted").count()

    return render(request, "landlord_dashboard.html", {
        "applications": applications,
        "properties": properties,
        "payments": payments,
        "landlord_inbox": landlord_inbox,
        "new_message_count": new_message_count,
    })
