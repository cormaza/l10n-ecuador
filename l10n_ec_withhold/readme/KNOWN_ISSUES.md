`l10n_ec_account_edi/tests/test_common.py`, in `_l10n_ec_create_form_move`, writes
`partner_id` before `journal_id`. In 19.0 the account move form hides `journal_id`
once a partner is set, so passing a journal to that helper fails with
`AssertionError: can't write on invisible field 'journal_id'`.

The helper should set the journal before the partner. Until it does, the tests in
this module do not pass a journal to `_l10n_ec_create_form_move` and rely on the
default journal resolution of the form, which for an `ec_dt_01` vendor bill is
`company_data["default_journal_purchase"]`.
