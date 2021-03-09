from decimal import Decimal
from django.conf import settings

from shop.models import Product
from coupons.models import Coupon

class Cart:
    """
    Notice: convert product id into String because Django
    uses JSON to serialize session data and JSON only allows String
    key names
    """

    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        self.coupon_id = self.session.get('coupon_id')
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # Save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override=False):
        """
        Add a product to the cart ur update its quantity.
        :param product: product instance
        :param override bool, qt should be override or incremented by the quantity
        :param quantity: integer number for qt
        :return: None
        """
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0, 'price': str(product.price)}
        if override:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity

        self.save()

    def remove(self, product):
        """
        Remove a product from the cart
        :param product: product instance
        :return: None
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products from the database
        :return: QuerySet products
        """
        product_ids = self.cart.keys()
        # Get the product objects and add them to the cart
        products = Product.objects.filter(id__in=product_ids)

        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """
        Count all items in the cart.
        :return: Integer
        """
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """
        calculate the total cost of the items in the cart
        """
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def save(self):
        """
         Make the session as 'modified' to make sure it gets saved.
         This tells Django that the session has changed and needs to be saved.
        """
        self.session.modified = True

    def clear(self):
        """
        Remove cart from Session
        """
        del self.session[settings.CART_SESSION_ID]
        self.save()

    @property
    def coupon(self):
        if self.coupon_id:
            try:
                return Coupon.objects.get(id=self.coupon_id)
            except Coupon.DoesNotExist:
                pass
            return None

    def get_discount(self):
        if self.coupon:
            return (self.coupon.discount / Decimal(100)) * self.get_total_price()
        return Decimal(0)

    def get_total_price_after_discount(self):
        return self.get_total_price() - self.get_discount()

