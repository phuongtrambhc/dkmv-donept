from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse

from carts.views import _cart_id
from carts.models import CartItem, Cart

from .models import Product, ProductVariant
from .forms import ProductForm, ProductVariantForm

from category.models import Category


# ===============================
# AJAX VIEW: KIỂM TRA TỒN KHO
# ===============================
def check_variation_stock(request):
    if request.method == 'GET':
        # Lấy giá trị từ AJAX
        product_id = request.GET.get('product_id')
        color = request.GET.get('color', '').strip().lower()
        size = request.GET.get('size', '').strip().upper()

        # Kiểm tra sự tồn tại của biến thể
        try:
            variant = ProductVariant.objects.get(
                product_id=product_id,
                color__iexact=color,
                size__iexact=size
            )

            stock_count = variant.stock

            if stock_count > 0:
                return JsonResponse({'available': True, 'stock': stock_count})
            else:
                return JsonResponse({'available': False, 'stock': 0, 'message': 'Out of Stock'})

        except ProductVariant.DoesNotExist:
            return JsonResponse({'available': False, 'message': 'Variation not available.'})

    return JsonResponse({'error': 'Invalid method.'}, status=400)


# ===============================
# STORE – TRANG KHÁCH HÀNG (ĐÃ SỬA: Thêm logic lọc giá)
# ===============================
def store(request, category_slug=None):
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=category, is_available=True)
    else:
        # Bắt đầu với tất cả sản phẩm có sẵn
        products = Product.objects.filter(is_available=True).order_by("id")

    # THÊM LOGIC LỌC THEO GIÁ
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # Tiếp tục phân trang như cũ
    paginator = Paginator(products, 10)
    page = request.GET.get("page")
    page_products = paginator.get_page(page)

    return render(request, "store/store.html", {
        "products": page_products,
        "product_count": products.count(),
    })


def product_detail(request, category_slug, product_slug):
    product = get_object_or_404(Product, category__slug=category_slug, slug=product_slug)
    categories = Category.objects.all()

    # THAY ĐỔI: Lấy danh sách màu sắc và kích thước từ các biến thể
    variants = ProductVariant.objects.filter(product=product)
    colors = variants.values_list("color", flat=True).distinct()
    sizes = variants.values_list("size", flat=True).distinct()

    total_stock = sum(v.stock for v in variants)

    return render(request, "store/product_detail.html", {
        "single_product": product,
        "colors": colors,  # THAY ĐỔI: Truyền biến 'colors'
        "sizes": sizes,  # THAY ĐỔI: Truyền biến 'sizes'
        "total_stock": total_stock,
        'categories': categories,
    })


def get_sizes(request, product_id):
    color = request.GET.get("color", "").strip()

    variants = ProductVariant.objects.filter(
        product_id=product_id,
        color__iexact=color,
    )

    sizes = variants.values_list("size", flat=True).distinct()

    return JsonResponse({"sizes": list(sizes)})


def search(request):
    keyword = request.GET.get("keyword", "")
    if keyword:
        products = Product.objects.filter(
            Q(description__icontains=keyword) |
            Q(product_name__icontains=keyword)
        )
    else:
        products = Product.objects.all()

    return render(request, "store/store.html", {
        "products": products,
        "product_count": len(products),
    })


# ===============================
# STAFF – QUẢN LÝ SẢN PHẨM
# ===============================
@login_required(login_url="login")
def staff_product_list(request):
    categories = Category.objects.all().order_by('category_name')
    category_filter = request.GET.get('category', 'all')

    if category_filter == "all":
        products = Product.objects.all().order_by('-id')
    else:
        products = Product.objects.filter(category__id=category_filter).order_by('-id')

    return render(request, 'store/staff_product_list.html', {
        'products': products,
        'categories': categories,
        'category_filter': category_filter,
    })


@login_required(login_url="login")
def staff_product_create(request):
    if not request.user.is_staff:
        return redirect("dashboard")

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully.")
            return redirect("staff_product_list")
    else:
        form = ProductForm()

    return render(request, "store/staff_product_form.html", {
        "form": form,
        "title": "Thêm sản phẩm",
    })


@login_required(login_url="login")
def staff_product_update(request, pk):
    if not request.user.is_staff:
        return redirect("dashboard")

    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect("staff_product_list")
    else:
        form = ProductForm(instance=product)

    return render(request, "store/staff_product_form.html", {
        "form": form,
        "title": "Sửa sản phẩm",
    })


@login_required(login_url="login")
def staff_product_delete(request, pk):
    if not request.user.is_staff:
        return redirect("dashboard")

    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect("staff_product_list")


# ===============================
# STAFF – QUẢN LÝ COMBO (COLOR + SIZE)
# ===============================
@login_required(login_url="login")
def staff_variant_by_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # 👈 THAY ĐỔI: Thêm lệnh sắp xếp (order_by)
    # Sắp xếp theo Màu (color) trước, sau đó sắp xếp theo Size (size)
    combos = ProductVariant.objects.filter(product=product).order_by('color', 'size')

    return render(request, "store/staff_variant_list.html", {
        "product": product,
        "combos": combos,
    })


@login_required(login_url="login")
def staff_variant_create(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product
            variant.save()
            messages.success(request, "Variant added successfully.")
            return redirect("staff_variant_by_product", product_id=product.id)
    else:
        form = ProductVariantForm()

    return render(request, "store/staff_variant_form.html", {
        "form": form,
        "title": "Thêm combo",
        "product": product,
    })


@login_required(login_url="login")
def staff_variant_update(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product

    if request.method == "POST":
        form = ProductVariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            messages.success(request, "Variant updated successfully.")
            return redirect("staff_variant_by_product", product_id=product.id)
    else:
        form = ProductVariantForm(instance=variant)

    return render(request, "store/staff_variant_form.html", {
        "form": form,
        "title": "Sửa combo",
        "product": product,
    })


@login_required(login_url="login")
def staff_variant_delete(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product_id = variant.product.id
    variant.delete()
    messages.success(request, "Variant deleted successfully.")
    return redirect("staff_variant_by_product", product_id=product_id)


# ===============================
# ADD TO CART
# ===============================
def add_cart(request, product_id):
    product = Product.objects.get(id=product_id)

    color = request.POST.get("color")
    size = request.POST.get("size")

    if color:
        color = color.lower().strip()
    if size:
        size = size.upper().strip()

    try:
        variant = ProductVariant.objects.get(product=product, color=color, size=size)
    except ProductVariant.DoesNotExist:
        messages.error(request, "Variation does not exist.")
        return redirect(request.META.get("HTTP_REFERER"))

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))

    try:
        cart_item = CartItem.objects.get(product=product, variant=variant, cart=cart)
        if cart_item.quantity < variant.stock:
            cart_item.quantity += 1
        else:
            messages.warning(request, "Insufficient stock.")
            return redirect(request.META.get("HTTP_REFERER"))
    except CartItem.DoesNotExist:
        cart_item = CartItem.objects.create(product=product, variant=variant, cart=cart, quantity=1)

    cart_item.save()
    return redirect("cart")


# ===============================
# STAFF – QUẢN LÝ DANH MỤC
# ===============================
@login_required(login_url="login")
def staff_category_list(request):
    categories = Category.objects.all().order_by('id')
    return render(request, "store/staff_category_list.html", {
        "categories": categories,
    })


@login_required(login_url="login")
def staff_category_add(request):
    if not request.user.is_staff:
        return redirect("dashboard")

    if request.method == "POST":
        Category.objects.create(
            category_name=request.POST.get("name"),
            slug=request.POST.get("slug"),
        )
        messages.success(request, "Category added successfully.")
        return redirect("staff_category_list")

    return render(request, "store/staff_category_form.html")


@login_required(login_url="login")
def staff_category_edit(request, id):
    if not request.user.is_staff:
        return redirect("dashboard")

    category = get_object_or_404(Category, id=id)

    if request.method == "POST":
        category.category_name = request.POST.get("name")
        category.slug = request.POST.get("slug")
        category.save()
        messages.success(request, "Category updated successfully.")
        return redirect("staff_category_list")

    return render(request, "store/staff_category_form.html", {
        "category": category
    })


@login_required(login_url="login")
def staff_category_delete(request, id):
    if not request.user.is_staff:
        return redirect("dashboard")

    category = get_object_or_404(Category, id=id)
    category.delete()
    messages.success(request, "Category deleted successfully.")
    return redirect("staff_category_list")