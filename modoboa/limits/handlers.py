"""Django signal handlers for limits."""

from django.db.models import signals
from django.dispatch import receiver

from django.contrib.contenttypes.models import ContentType

from modoboa.admin import models as admin_models
from modoboa.admin import signals as admin_signals
from modoboa.core import models as core_models
from modoboa.core import signals as core_signals
from modoboa.lib import signals as lib_signals
from modoboa.parameters import tools as param_tools

from . import lib
from . import models
from . import utils


@receiver(core_signals.can_create_object)
def check_object_limit(sender, context, object_type, **kwargs):
    """Check if user can create a new object."""
    if context.__class__.__name__ == "User":
        if not param_tools.get_global_parameter("enable_admin_limits"):
            return
        if context.is_superuser:
            return True
        limit = context.userobjectlimit_set.get(name=object_type)
    elif context.__class__.__name__ == "Domain":
        if not param_tools.get_global_parameter("enable_domain_limits"):
            return
        limit = context.domainobjectlimit_set.get(name=object_type)
    else:
        raise NotImplementedError
    count = kwargs.get("count", 1)
    if limit.is_exceeded(count):
        raise lib.LimitReached(limit)


@receiver(signals.post_save, sender=core_models.User)
def create_user_limits(sender, instance, **kwargs):
    """Create limits for new user."""
    if not kwargs.get("created"):
        return
    request = lib_signals.get_request()
    creator = request.user if request else None
    global_params = dict(param_tools.get_global_parameters("limits"))
    for name, definition in utils.get_user_limit_templates():
        ct = ContentType.objects.get_by_natural_key(
            *definition["content_type"].split("."))
        max_value = 0
        # creator can be None if user was created by a factory
        if not creator or creator.is_superuser:
            max_value = global_params["deflt_user_{0}_limit".format(name)]
        models.UserObjectLimit.objects.create(
            user=instance, name=name, content_type=ct, max_value=max_value)


@receiver(signals.post_save, sender=admin_models.Domain)
def create_domain_limits(sender, instance, **kwargs):
    """Create limits for new domain."""
    if not kwargs.get("created"):
        return
    global_params = dict(param_tools.get_global_parameters("limits"))
    for name, definition in utils.get_domain_limit_templates():
        max_value = global_params["deflt_domain_{0}_limit".format(name)]
        models.DomainObjectLimit.objects.create(
            domain=instance, name=name, max_value=max_value)


@receiver(admin_signals.extra_domain_dashboard_widgets)
def display_domain_limits(sender, user, domain, **kwargs):
    """Display resources usage for domain."""
    if not param_tools.get_global_parameter("enable_domain_limits"):
        return []
    return [{
        "column": "right",
        "template": "limits/resources_widget.html",
        "context": {
            "limits": domain.domainobjectlimit_set.all()
        }
    }]


@receiver(admin_signals.extra_account_dashboard_widgets)
def display_admin_limits(sender, user, account, **kwargs):
    """Display resources usage for admin."""
    condition = (
        param_tools.get_global_parameter("enable_admin_limits") and
        account.role in ["DomainAdmins", "Resellers"]
    )
    if not condition:
        return []
    return [{
        "column": "right",
        "template": "limits/resources_widget.html",
        "context": {
            "limits": (
                account.userobjectlimit_set.select_related("content_type"))
        }
    }]
