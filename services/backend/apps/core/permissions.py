from rest_framework.permissions import BasePermission


class IsNGOAdmin(BasePermission):
    message = "NGO admin access required"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == "ngo_admin"
        )


class IsNGOAdminWithNGO(BasePermission):
    message = "NGO admin access required — complete NGO setup first"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == "ngo_admin"
            and bool(getattr(user, "ngo_id", None))
        )


class IsVolunteer(BasePermission):
    message = "Volunteer access required"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == "volunteer"
        )


class IsVolunteerWithNGO(BasePermission):
    message = "Volunteer NGO not configured"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == "volunteer"
            and bool(getattr(user, "ngo_id", None))
        )


def assert_same_ngo(resource_ngo_id: str, user) -> None:
    """Raises PermissionDenied if resource NGO does not match user NGO."""
    from rest_framework.exceptions import PermissionDenied
    if getattr(user, "ngo_id", None) != resource_ngo_id:
        raise PermissionDenied("Cross-NGO access denied")
