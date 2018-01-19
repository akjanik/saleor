import datetime
import json
from random import randint

from django.conf import settings
from django.http import HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from ..cart.utils import set_cart_cookie
from ..core.utils import get_paginator_items, serialize_decimal
from ..core.utils.filters import get_now_sorted_by
from .filters import ProductFilter, SORT_BY_FIELDS
from .models import Category, Product
from .utils import (
    get_availability, get_product_attributes_data, get_product_images,
    get_variant_picker_data, handle_cart_form, product_json_ld,
    products_for_cart, products_with_availability, products_with_details)


def product_details(request, slug, product_id, form=None):
    """Product details page

    The following variables are available to the template:

    product:
        The Product instance itself.

    is_visible:
        Whether the product is visible to regular users (for cases when an
        admin is previewing a product before publishing).

    form:
        The add-to-cart form.

    price_range:
        The PriceRange for the product including all discounts.

    undiscounted_price_range:
        The PriceRange excluding all discounts.

    discount:
        Either a Price instance equal to the discount value or None if no
        discount was available.

    local_price_range:
        The same PriceRange from price_range represented in user's local
        currency. The value will be None if exchange rate is not available or
        the local currency is the same as site's default currency.
    """
    products = products_with_details(user=request.user)
    product = get_object_or_404(products, id=product_id)
    if product.get_slug() != slug:
        return HttpResponsePermanentRedirect(product.get_absolute_url())
    today = datetime.date.today()
    is_visible = (
        product.available_on is None or product.available_on <= today)
    if form is None:
        form = handle_cart_form(request, product, create_cart=False)[0]
    availability = get_availability(product, discounts=request.discounts,
                                    local_currency=request.currency)
    product_images = get_product_images(product)
    variant_picker_data = get_variant_picker_data(
        product, request.discounts, request.currency)
    product_attributes = get_product_attributes_data(product)
    # show_variant_picker determines if variant picker is used or select input
    show_variant_picker = all([v.attributes for v in product.variants.all()])
    json_ld_data = product_json_ld(product, product_attributes)
    return TemplateResponse(
        request, 'product/details.html',
        {'is_visible': is_visible,
         'form': form,
         'availability': availability,
         'product': product,
         'product_attributes': product_attributes,
         'product_images': product_images,
         'show_variant_picker': show_variant_picker,
         'variant_picker_data': json.dumps(
             variant_picker_data, default=serialize_decimal),
         'json_ld_product_data': json.dumps(
             json_ld_data, default=serialize_decimal)})


def product_add_to_cart(request, slug, product_id):
    # types: (int, str, dict) -> None

    if not request.method == 'POST':
        return redirect(reverse(
            'product:details',
            kwargs={'product_id': product_id, 'slug': slug}))

    products = products_for_cart(user=request.user)
    product = get_object_or_404(products, pk=product_id)
    form, cart = handle_cart_form(request, product, create_cart=True)
    if form.is_valid():
        form.save()
        if request.is_ajax():
            response = JsonResponse({'next': reverse('cart:index')}, status=200)
        else:
            response = redirect('cart:index')
    else:
        if request.is_ajax():
            response = JsonResponse({'error': form.errors}, status=400)
        else:
            response = product_details(request, slug, product_id, form)
    if not request.user.is_authenticated:
        set_cart_cookie(cart, response)
    return response


def category_index(request, path, category_id):
    category = get_object_or_404(Category, id=category_id)
    actual_path = category.get_full_path()
    if actual_path != path:
        return redirect('product:category', permanent=True, path=actual_path,
                        category_id=category_id)
    products = products_with_details(user=request.user).filter(
        category__id=category.id).order_by('name')
    product_filter = ProductFilter(
        request.GET, queryset=products, category=category)
    products_paginated = get_paginator_items(
        product_filter.qs, settings.PAGINATE_BY, request.GET.get('page'))
    products_and_availability = list(products_with_availability(
        products_paginated, request.discounts, request.currency))
    now_sorted_by = get_now_sorted_by(product_filter)
    arg_sort_by = request.GET.get('sort_by')
    is_descending = arg_sort_by.startswith('-') if arg_sort_by else False
    ctx = {'category': category, 'filter_set': product_filter,
           'products': products_and_availability,
           'products_paginated': products_paginated,
           'sort_by_choices': SORT_BY_FIELDS,
           'now_sorted_by': now_sorted_by,
           'is_descending': is_descending}
    return TemplateResponse(request, 'category/index.html', ctx)


def products_from_collections(request, product_id):
    products = Product.objects.prefetch_related(
        'collections', 'images').filter(
        collections__products__id=product_id).exclude(
        id=product_id).distinct()
    products_count = products.count()
    if products_count > 6:
        index = randint(0, products_count - 6)
    else:
        index = 0

    ctx = {'products': products[index:index + 6]}
    return TemplateResponse(request, 'product/_product_collections.html', ctx)
