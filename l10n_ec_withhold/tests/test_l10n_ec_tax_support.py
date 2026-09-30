from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ec_account_edi.tests.test_edi_common import TestL10nECEdiCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nEcTaxSupport(TestL10nECEdiCommon):
    """``l10n_ec_tax_support`` is seeded from the partner and enforced on post.

    Only the behaviour the module implements is asserted here; the field is a
    ``Selection`` fed by ``TAX_SUPPORT``, which is the ORM's business.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.position_require_withhold = cls.env["account.fiscal.position"].create(
            {"name": "Withhold", "l10n_ec_avoid_withhold": False}
        )

    def test_01_partner_tax_support_seeds_the_move(self):
        self.partner_ruc.l10n_ec_tax_support = "14"
        move = self._l10n_ec_create_in_invoice(self.partner_ruc, auto_post=False)
        move.l10n_ec_tax_support = False
        self.assertEqual(move._get_l10n_ec_tax_support(), "14")

    def test_02_unknown_code_is_refused(self):
        move = self._l10n_ec_create_in_invoice(self.partner_ruc, auto_post=False)
        with self.assertRaises(ValueError):
            move.l10n_ec_tax_support = "99"

    def test_03_posting_refuses_a_purchase_document_without_support(self):
        invoice = self._l10n_ec_create_in_invoice(self.partner_ruc, auto_post=False)
        invoice.fiscal_position_id = self.position_require_withhold
        invoice.l10n_ec_tax_support = False
        invoice.invoice_line_ids.l10n_ec_tax_support = False
        with self.assertRaisesRegex(UserError, "Please fill a Tax Support"):
            invoice.action_post()
