from odoo import models


class AccountEdiFormat(models.Model):

    _inherit = "account.edi.format"

    def _is_compatible_with_journal(self, journal):
        if journal.country_code != "EC":
            super(AccountEdiFormat, self)._is_compatible_with_journal(journal)
        return False

    def _is_enabled_by_default_on_journal(self, journal):
        if journal.country_code != "EC":
            super(AccountEdiFormat, self)._is_enabled_by_default_on_journal(journal)
        return False

    def _is_required_for_invoice(self, invoice):
        if invoice.country_code != "EC":
            return super(AccountEdiFormat, self)._is_required_for_invoice(invoice)
        return False
