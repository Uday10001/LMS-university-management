from apps.academic.models import Section


def sidebar_context(request):
    """
    Injects sidebar data for all templates.
    """
    context = {}

    if request.user.is_authenticated:
        if request.user.user_type == 'management':
            context['all_sections'] = Section.objects.all().order_by('semester', 'code')

    return context