@admin.register(FinancialEntry)
class FinancialEntryAdmin(admin.ModelAdmin):

    list_display = (
        "category",
        "description",
        "amount",
        "month",
        "year",
        "property_name",
        "sheet_name",
        "row_number",
    )

    list_filter = (
        "year",
        "month",
        "category",
        "sheet_name",
    )

    search_fields = (
        "description",
        "category",
        "property_name",
        "sheet_name",
    )

    ordering = (
        "year",
        "month",
        "category",
    )

    readonly_fields = (
        "upload",
        "property_name",
        "sheet_name",
        "row_number",
        "entry_date",
        "month",
        "year",
        "entry_type",
        "category",
        "description",
        "amount",
        "created_at",
    )

    def has_add_permission(self, request):
        return False
