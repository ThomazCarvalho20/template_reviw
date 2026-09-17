from apps.core.domain import NavigationService


def navigation_settings(request):
    return NavigationService.build_navigation_context(request)
