from datetime import datetime

from random import randint
from locust import task, constant_pacing

from common import User


def create_random_uid():
    return '%05d-%03d-%04d' % (randint(1, 99999), randint(1, 999), randint(1, 9999))


class PosCachier(User):
    config_ids = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos_data = None
        self.coupon_data = None
        self.threads = []

    def on_start(self):
        super().on_start()
        pos_config = self.client.get_model('pos.config')
        pos_session = self.client.get_model('pos.session')
        # Try to use one config per user, loop back to the beginning if we run out of configs.
        if not self.config_ids:
            self.config_ids = pos_config.search([])
        config_id = self.config_ids[self.id % len(self.config_ids)]
        # Open the POS from the backend
        pos_config.open_session_cb(config_id)
        pos_config.open_ui(config_id)
        # Find the session created by open_ui
        self.session_id = pos_config.read(config_id, ['current_session_id'])['current_session_id'][0]

        self.partners = self.client.get_model('res.partner').search_read([], [
            "name",
            "street",
            "city",
            "state_id",
            "country_id",
            "vat",
            "phone",
            "zip",
            "mobile",
            "email",
            "barcode",
            "write_date",
            "property_account_position_id",
            "property_product_pricelist"
        ])

        self.products = self.client.get_model('product.product').search_read([
            ("sale_ok", "=", True),
            ("available_in_pos", "=", True),
        ], [
            "display_name",
            "lst_price",
            "standard_price",
            "categ_id",
            "pos_categ_id",
            "taxes_id",
            "barcode",
            "default_code",
            "to_weight",
            "uom_id",
            "description_sale",
            "description",
            "product_tmpl_id",
            "tracking"
        ])

    @task(1)
    def sell_pos_order(self):
        number_of_lines = randint(1, 5)
        lines = []
        amount_total = 0
        for i in range(number_of_lines):
            product = self.products[randint(0, len(self.products) - 1)]
            qty = randint(1, 10)
            price_subtotal = product['lst_price'] * qty
            amount_total += price_subtotal
            lines.append([0, 0, {
                'product_id': product['id'],
                'qty': qty,
                'price_unit': product['lst_price'],
                'price_subtotal': price_subtotal,
                'price_subtotal_incl': price_subtotal,
                'discount': 0,
                'tax_ids': [[6, 0, product['taxes_id']]],
            }])
        uid = create_random_uid()
        order = {
            'id': uid,
            'data': {
                'name': 'POS Order' + uid,
                'amount_paid': amount_total,
                'amount_total': amount_total,
                'amount_tax': 0,
                'amount_return': 0,
                'lines': lines,
                'statement_ids': [[0, 0, {
                    'name': self.today.strftime('%Y-%m-%d %H:%M:%S'),
                    'payment_method_id': 1,
                    'amount': amount_total,
                    'payment_status': '',
                    'ticket': '',
                    'card_type': '',
                    'transaction_id': '',
                }]],
                'pos_session_id': self.session_id,
                'pricelist_id': 1,
                'partner_id': self.partners[randint(0, len(self.partners) - 1)]['id'],
                'user_id': 2,
                'employee_id': None,
                'uid': uid,
                'sequence_number': 1,
                'creation_date': self.today.strftime('%Y-%m-%d %H:%M:%S'),
                'fiscal_position_id': False,
                'server_id': False,
                'to_invoice': False
            }
        }

        self.client.get_model('pos.order').create_from_ui([order])
