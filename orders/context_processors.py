from .models import Cart

def cart_context(request):
    """
    Global context processor to attach the total cart item count
    to every template rendering for the authenticated customer.
    """
    if request.user.is_authenticated and getattr(request.user, 'role', None) in (None, 'customer'):
        cart = Cart.objects.filter(user=request.user, status=Cart.STATUS_ACTIVE).first()
        if cart:
            # Sum up actual quantity of all items, not just distinct products
            count = sum(item.quantity for item in cart.items.all())
            return {'cart_item_count': count}
    return {'cart_item_count': 0}
