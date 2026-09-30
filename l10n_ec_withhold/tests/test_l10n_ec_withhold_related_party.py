from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ec_account_edi.tests.sri_response import patch_service_sri
from odoo.addons.l10n_ec_account_edi.tests.test_edi_common import TestL10nECEdiCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nWithholdRelatedParty(TestL10nECEdiCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ec")
    @AccountTestInvoicingCommon.setup_chart_template("ec")
    def setUpClass(cls):
        super().setUpClass()
        cls.WizardWithhold = cls.env["l10n_ec.wizard.create.purchase.withhold"]
        cls.position_require_withhold = cls.env["account.fiscal.position"].create(
            {"name": "Withhold", "l10n_ec_avoid_withhold": False}
        )
        cls.company.property_account_position_id = cls.position_require_withhold
        cls.chart_template = cls.env["account.chart.template"].with_company(cls.company)
        cls.tax_vat = cls.chart_template.ref("tax_vat_510_sup_01")
        cls.tax_withhold_vat_100 = cls.chart_template.ref("tax_withhold_vat_100")
        cls.journal_purchase_withhold = cls.chart_template.ref("purchase_withhold_ec")
        cls.journal_purchase_withhold.l10n_ec_emission_address_id = (
            cls.partner_contact.id
        )
        # Same shadow as ``test_l10n_ec_purchase_withhold``: 19.0 ships two
        # purchase journals and the inherited ``journal_purchase`` is the
        # liquidation one, which an ``ec_dt_01`` bill must not use.
        cls.journal_purchase = cls.company_data["default_journal_purchase"]

    def setUp(self):
        super().setUp()
        # ``_setup_edi_company_ec`` configures the vendor-bill journal and is
        # not idempotent: it re-writes ``l10n_latam_use_documents``, which
        # ``l10n_latam_invoice_document`` refuses once the journal holds
        # validated documents. One call per test, before any bill is posted.
        self._setup_edi_company_ec()

    def _create_ruc_partner(self, name, vat, related_party=False):
        return self.Partner.create(
            {
                "name": name,
                "vat": vat,
                "l10n_latam_identification_type_id": self.env.ref("l10n_ec.ec_ruc").id,
                "country_id": self.env.ref("base.ec").id,
                "l10n_ec_related_party": related_party,
            }
        )

    def _create_partner_withhold_edi_document(self, partner):
        """Return the EDI document of the purchase withhold of ``partner``'s bill.

        The withhold is reached the way a user reaches it: post the vendor bill,
        run ``action_try_create_ecuadorian_withhold()`` and confirm the wizard.
        The ``account.edi.document`` is then the one ``_post()`` creates, which
        is also what the ``parteRel`` assertion is about -- a hand-built move
        would keep passing even if the wizard or the posting stopped producing
        a document.
        """
        partner.property_account_position_id = self.position_require_withhold
        # The journal is left to the form default (the ordinary vendor-bill
        # one, pinned by ``cls.journal_purchase`` in ``setUpClass``), which is
        # what the interface resolves for an ``ec_dt_01`` bill.
        invoice_form = self._l10n_ec_create_form_move(
            move_type="in_invoice",
            internal_type="invoice",
            partner=partner,
            taxes=self.tax_vat,
            latam_document_type=self.env.ref("l10n_ec.ec_dt_01"),
        )
        invoice_form.l10n_ec_tax_support = "01"
        invoice_form.l10n_latam_document_number = self.get_sequence_number()
        invoice_form.l10n_ec_electronic_authorization = (
            self.number_authorization_electronic
        )
        invoice = invoice_form.save()
        invoice.action_post()
        invoice.action_try_create_ecuadorian_withhold()
        wizard_form = Form(
            self.WizardWithhold.with_context(
                active_ids=invoice.ids, default_partner_id=invoice.partner_id.id
            )
        )
        wizard_form.issue_date = invoice.invoice_date
        wizard_form.journal_id = self.journal_purchase_withhold
        with wizard_form.withhold_line_ids.new() as line:
            line.invoice_id = invoice
            line.tax_group_withhold_id = self.tax_withhold_vat_100.tax_group_id
            line.tax_withhold_id = self.tax_withhold_vat_100
            line.l10n_ec_tax_support = "01"
        wizard = wizard_form.save()
        wizard.button_validate()
        withhold = invoice.l10n_ec_withhold_ids
        self.assertEqual(len(withhold), 1)
        return withhold._get_edi_document(self.edi_format)

    def test_01_l10n_ec_related_party_defaults_to_false(self):
        """The assertion field starts unset, never preselected."""
        partner = self._create_ruc_partner("Test Partner Unrelated", "1313109678002")
        self.assertFalse(partner.l10n_ec_related_party)

    @patch_service_sri
    def test_02_l10n_ec_parte_rel_is_no_when_unset(self):
        edi_doc = self._create_partner_withhold_edi_document(self.partner_ruc)
        self.assertFalse(self.partner_ruc.l10n_ec_related_party)
        self.assertEqual(edi_doc._l10n_ec_get_info_withhold()["parteRel"], "NO")

    @patch_service_sri
    def test_03_l10n_ec_parte_rel_is_si_when_related_party(self):
        self.partner_ruc.l10n_ec_related_party = True
        edi_doc = self._create_partner_withhold_edi_document(self.partner_ruc)
        self.assertEqual(edi_doc._l10n_ec_get_info_withhold()["parteRel"], "SI")

    @patch_service_sri
    def test_04_l10n_ec_related_party_is_per_partner(self):
        """Asserting SI for one partner must not change another's withhold."""
        partner = self._create_ruc_partner(
            "Test Partner Related", "1313109678003", related_party=True
        )
        related_doc = self._create_partner_withhold_edi_document(partner)
        unrelated_doc = self._create_partner_withhold_edi_document(self.partner_ruc)
        self.assertEqual(related_doc._l10n_ec_get_info_withhold()["parteRel"], "SI")
        self.assertEqual(unrelated_doc._l10n_ec_get_info_withhold()["parteRel"], "NO")

    @patch_service_sri
    def test_05_l10n_ec_parte_rel_reaches_the_rendered_xml(self):
        """Close the loop field -> ``_l10n_ec_get_info_withhold`` -> XML.

        The builder asserts the dict key; this asserts the ``parteRel`` element
        the SRI actually reads, so a renamed key or a template drift cannot
        pass silently. ``SI`` and ``NO`` are the only values the XSD simpleType
        ``parteRel`` accepts.
        """
        self.partner_ruc.l10n_ec_related_party = True
        related_doc = self._create_partner_withhold_edi_document(self.partner_ruc)
        self.assertIn("<parteRel>SI</parteRel>", related_doc._l10n_ec_render_xml_edi())
        self.partner_ruc.l10n_ec_related_party = False
        unrelated_doc = self._create_partner_withhold_edi_document(self.partner_ruc)
        self.assertIn(
            "<parteRel>NO</parteRel>", unrelated_doc._l10n_ec_render_xml_edi()
        )
