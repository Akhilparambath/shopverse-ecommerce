from .models import Cart, Category


def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        count = Cart.objects.filter(user=request.user).count()
    return {'cart_count': count}


def categories_list(request):
    return {'all_categories': Category.objects.all()}
