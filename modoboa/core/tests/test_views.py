"""Core views test cases."""

from testfixtures import compare

from django import forms
from django.core.urlresolvers import reverse

from modoboa.lib.tests import ModoTestCase
from modoboa.parameters import forms as param_forms
from modoboa.parameters import tools as param_tools

from .. import factories
from .. import models


class DashboardTestCase(ModoTestCase):
    """Dashboard tests."""

    @classmethod
    def setUpTestData(cls):
        """Create some data."""
        super(DashboardTestCase, cls).setUpTestData()
        cls.dadmin = factories.UserFactory(
            username="admin@test.com", groups=("DomainAdmins",)
        )
        cls.user = factories.UserFactory(
            username="user@test.com", groups=("SimpleUsers",)
        )

    def test_access(self):
        """Load dashboard."""
        url = reverse("core:dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Latest news", response.content)
        self.client.logout()
        self.client.login(username=self.dadmin.username, password="toto")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Latest news", response.content)
        self.client.logout()
        self.client.login(username=self.user.username, password="toto")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_root_dispatch(self):
        """Check root dispatching."""
        url = reverse("core:root")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse("core:dashboard")))


class SettingsTestCase(ModoTestCase):
    """Settings tests."""

    settings_sample = {
        "core-check_new_versions": "True",
        "core-log_maximum_age": "365",
        "core-ldap_auth_method": "searchbind",
        "limits-deflt_domain_mailbox_aliases_limit": "0",
        "core-send_statistics": "True",
        "core-default_top_redirection": "user",
        "core-sender_address": "noreply@modoboa.org",
        "admin-auto_account_removal": "False",
        "core-ldap_server_port": "389",
        "core-rounds_number": "70000",
        "core-ldap_bind_password": "",
        "limits-deflt_domain_domain_aliases_limit": "0",
        "core-secret_key": ":?j3]QPWo!.'_c4n",
        "relaydomains-master_cf_path": "/etc/postfix/master.cf",
        "limits-deflt_domain_domain_admins_limit": "0",
        "limits-enable_admin_limits": "True",
        "core-ldap_bind_dn": "",
        "core-enable_api_communication": "True",
        "limits-deflt_user_domain_admins_limit": "0",
        "limits-enable_domain_limits": "False",
        "csrfmiddlewaretoken": "SGgMVZsA4TPqoiV786TMST6xgOlhAf4F",
        "limits-deflt_user_mailboxes_limit": "0",
        "core-password_scheme": "sha512crypt",
        "core-items_per_page": "30",
        "limits-deflt_user_mailbox_aliases_limit": "0",
        "limits-deflt_domain_mailboxes_limit": "0",
        "core-ldap_is_active_directory": "False",
        "core-ldap_group_type": "posixgroup",
        "limits-deflt_user_domain_aliases_limit": "0",
        "core-top_notifications_check_interval": "30",
        "core-ldap_password_attribute": "userPassword",
        "admin-auto_create_domain_and_mailbox": "True",
        "admin-enable_dnsbl_checks": "True",
        "admin-default_domain_quota": "0",
        "core-ldap_server_address": "localhost",
        "core-authentication_type": "local",
        "core-ldap_admin_groups": "",
        "core-ldap_groups_search_base": "",
        "admin-enable_mx_checks": "True",
        "core-ldap_search_base": "",
        "admin-valid_mxs": "",
        "limits-deflt_user_domains_limit": "0",
        "core-ldap_search_filter": "(mail=%(user)s)",
        "core-ldap_secured": "False",
        "core-ldap_user_dn_template": ""
    }

    def test_get_settings(self):
        """Test settings display."""
        url = reverse("core:parameters")
        response = self.ajax_get(url)
        for app in ["core", "admin", "limits", "relaydomains"]:
            self.assertIn('data-app="{}"'.format(app), response["content"])

    def test_save_settings(self):
        """Test settings save."""
        url = reverse("core:parameters")
        response = self.client.post(url, self.settings_sample, format="json")
        self.assertEqual(response.status_code, 200)
        self.settings_sample["core-rounds_number"] = ""
        response = self.client.post(url, self.settings_sample, format="json")
        self.assertEqual(response.status_code, 400)
        compare(response.json(), {
            "form_errors": {"rounds_number": ["This field is required."]},
            "prefix": "core"
        })


class UserSettings(param_forms.UserParametersForm):
    """Stupid user settings form."""

    app = "core"

    test = forms.CharField()


class PreferencesTestCase(ModoTestCase):
    """Test user preferences."""

    @classmethod
    def setUpClass(cls):
        """Register user form."""
        super(PreferencesTestCase, cls).setUpClass()
        param_tools.registry.add("user", UserSettings, "Test")

    @classmethod
    def tearDownClass(cls):
        """Remove user class."""
        super(PreferencesTestCase, cls).tearDownClass()
        del param_tools.registry._registry["user"]["core"]

    def test_get_preferences(self):
        """Test preferences display."""
        url = reverse("core:user_preferences")
        self.ajax_get(url)

    def test_save_preferences(self):
        """Test preferences save."""
        url = reverse("core:user_preferences")
        response = self.client.post(url, {"core-test": "toto"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), "Preferences saved")

        admin = models.User.objects.get(username="admin")
        self.assertEqual(admin.parameters.get_value("test"), "toto")
