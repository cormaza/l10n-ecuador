from . import controllers
from . import models
from . import wizard
from . import tests

from odoo import api, SUPERUSER_ID
from odoo.addons import account

native_auto_install_l10n = account._auto_install_l10n


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    payment_term_inmediate = env.ref("account.account_payment_term_immediate", False)
    if payment_term_inmediate:
        payment_term_inmediate.write({"l10n_ec_sri_type": "contado"})
    if (
        env["ir.module.module"].search_count(
            [("name", "=", "account_accountant"), ("state", "=", "installed")]
        )
        == 1
    ):
        accountant_menu = env.ref("account_accountant.menu_accounting")
        sri_menu = env.ref("l10n_ec_niif.sri_root_menu")
        sri_menu.write(
            {
                "parent_id": accountant_menu.id,
            }
        )


def _auto_install_l10n_ec(env):
    country_code = env.company.country_id.code
    if country_code:
        module_list = []
        if country_code != "EC":
            return native_auto_install_l10n(env)
        else:
            module_list.append("l10n_ec_niif")
            module_ids = env["ir.module.module"].search(
                [("name", "in", module_list), ("state", "=", "uninstalled")]
            )
            module_ids.sudo().button_install()


account._auto_install_l10n = _auto_install_l10n_ec
