from odoo import fields, models


class SriXmlInfoAditional(models.Model):
    _name = "sri.xml.info.aditional"
    _description = "Additional Info on RIDE"

    name = fields.Char(required=True)
    description = fields.Char(required=True)
    move_id = fields.Many2one(
        comodel_name="account.move", string="Account Move", ondelete="cascade"
    )
