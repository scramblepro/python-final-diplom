from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from backend.models import (
    Contact, Order, OrderItem, Parameter, ProductParameter, 
    Shop, Category, Product, ProductInfo, User
)
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, render
from django.utils.crypto import get_random_string
from .serializers import (
    BasketSerializer, CategorySerializer, ContactSerializer,
    OrderSerializer, ProductInfoSerializer, RegisterSerializer, 
    ShopSerializer
)
from backend.signals import new_user_registered
import json
import yaml


class RegisterAccount(APIView):
    """
    Регистрация покупателей
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'Status': True})
        return Response({'Status': False, 'Errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ConfirmAccount(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        token = request.data.get('token')

        if not email or not token:
            return Response({'Status': False, 'Errors': 'Не указаны email или token'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'Status': False, 'Errors': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        if user.confirmation_token != token:
            return Response({'Status': False, 'Errors': 'Неверный токен'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.confirmation_token = None
        user.save()
        return Response({'Status': True})


class LoginAccount(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        user = authenticate(username=request.data.get('email'), password=request.data.get('password'))
        if user:
            if user.is_active:
                token, _ = Token.objects.get_or_create(user=user)
                return Response({'Status': True, 'Token': token.key})
            return Response({'Status': False, 'Errors': 'Пользователь не активен'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'Status': False, 'Errors': 'Неверный логин или пароль'}, status=status.HTTP_401_UNAUTHORIZED)


class PartnerUpdate(APIView):
    """
    Загрузка прайс-листа поставщика (JSON или YAML)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.type != 'shop':
            return Response({'status': False, 'error': 'Только для пользователей типа "shop"'}, status=403)

        file = request.FILES.get('file')
        if not file:
            return Response({'status': False, 'error': 'Файл не передан'}, status=400)

        try:
            # Определяем формат файла
            if file.name.endswith('.yaml') or file.name.endswith('.yml'):
                data = yaml.safe_load(file)
            elif file.name.endswith('.json'):
                data = json.load(file)
            else:
                return Response({'status': False, 'error': 'Неверный формат файла'}, status=400)
        except Exception as e:
            return Response({'status': False, 'error': f'Ошибка чтения файла: {str(e)}'}, status=400)

        shop, _ = Shop.objects.get_or_create(name=data['shop'], user=user)

        with transaction.atomic():
            for category in data.get('categories', []):
                cat_obj, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                cat_obj.shops.add(shop)

            ProductInfo.objects.filter(shop=shop).delete()

            for item in data.get('goods', []):
                product, _ = Product.objects.get_or_create(
                    name=item['name'],
                    category_id=item['category']
                )

                product_info = ProductInfo.objects.create(
                    product=product,
                    shop=shop,
                    model=item.get('model', ''),
                    quantity=item.get('quantity', 0),
                    price=item.get('price', 0),
                    price_rrc=item.get('price_rrc', 0)
                )

                for name, value in item.get('parameters', {}).items():
                    param_obj, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(
                        product_info=product_info,
                        parameter=param_obj,
                        value=value
                    )

        return Response({'status': True, 'message': 'Прайс-лист успешно обновлен'})
    

class BasketView(APIView):
    """
    Работа с корзиной пользователя: просмотр, добавление, удаление товаров
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        basket, _ = Order.objects.get_or_create(user=request.user, state='basket')
        ordered_items = basket.ordered_items.select_related('product_info__product', 'product_info__shop')

        total_sum = sum([item.quantity * item.product_info.price for item in ordered_items])
        serializer = OrderSerializer(basket, context={'total_sum': total_sum})
        data = serializer.data
        data['total_sum'] = total_sum

        return Response(data)

    def post(self, request, *args, **kwargs):
        items = request.data.get('items')
        if not items:
            return Response({'Status': False, 'Error': 'Не передан список товаров'}, status=status.HTTP_400_BAD_REQUEST)

        basket, _ = Order.objects.get_or_create(user=request.user, state='basket')

        for item in items:
            product_info_id = item.get('product_info')
            quantity = item.get('quantity', 1)

            if not product_info_id:
                continue

            try:
                product_info = ProductInfo.objects.get(id=product_info_id)
            except ProductInfo.DoesNotExist:
                return Response({'Status': False, 'Error': f'product_info с id={product_info_id} не найден'}, status=404)

            OrderItem.objects.update_or_create(
                order=basket,
                product_info=product_info,
                defaults={'quantity': quantity}
            )

        return Response({'Status': True})

    def delete(self, request, *args, **kwargs):
        items = request.data.get('items')
        if not items:
            return Response({'Status': False, 'Error': 'Не передан список product_info для удаления'}, status=400)

        basket = Order.objects.filter(user=request.user, state='basket').first()
        if not basket:
            return Response({'Status': False, 'Error': 'Корзина не найдена'}, status=404)

        deleted_count = 0
        for item in items:
            product_info_id = item.get('product_info')
            if not product_info_id:
                continue

            deleted_count += OrderItem.objects.filter(
                order=basket,
                product_info_id=product_info_id
            ).delete()[0]

        return Response({'Status': True, 'Deleted': deleted_count})
    
class CategoryView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = []

class ShopView(ListAPIView):
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer
    permission_classes = [] 

class ProductInfoView(ListAPIView):
    queryset = ProductInfo.objects.select_related('product', 'shop', 'product__category')
    serializer_class = ProductInfoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['shop', 'product__category']
    search_fields = ['product__name']
    permission_classes = []


class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        contact_id = request.data.get("contact")

        if not contact_id:
            return Response({"status": False, "error": "Необходимо указать контакт"}, status=400)

        try:
            contact = Contact.objects.get(id=contact_id, user=user)
        except Contact.DoesNotExist:
            return Response({"status": False, "error": "Контакт не найден"}, status=404)

        basket = Order.objects.filter(user=user, state='basket').first()
        if not basket:
            return Response({"status": False, "error": "Корзина пуста"}, status=400)

        with transaction.atomic():
            basket.contact = contact
            basket.state = 'new'
            basket.save()

        # Email для пользователя
        send_mail(
            'Подтверждение заказа',
            f'Ваш заказ #{basket.id} успешно оформлен.',
            'no-reply@example.com',
            [user.email],
            fail_silently=False
        )

        # Email админу
        items = basket.ordered_items.select_related('product_info__product', 'product_info__shop')
        items_list = '\n'.join([
    f"{item.product_info.product.name} | {item.quantity} шт. | {item.product_info.price} ₽"
    for item in items
])

        admin_message = f"""
        Новый заказ #{basket.id}

        Пользователь: {user.email}
        Контакт:
          Город: {contact.city}
          Адрес: {contact.street}, {contact.house or '-'}
          Телефон: {contact.phone}

        Товары:
        {items_list}

        Итого: {sum([item.quantity * item.product_info.price for item in items])} ₽
        """

        send_mail(
            'Новый заказ от клиента',
            admin_message,
            'no-reply@example.com',
            ['admin@example.com'],
            fail_silently=False
        )
    
        return Response({'status': True, 'message': 'Заказ успешно оформлен'})

    def get(self, request, *args, **kwargs):
        """
        Получение списка заказов пользователя
        """
        orders = Order.objects.filter(user=request.user).select_related('contact').prefetch_related(
            'ordered_items__product_info__product', 
            'ordered_items__product_info__shop'
        )
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

class ContactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            contact = Contact.objects.get(id=pk, user=request.user)
        except Contact.DoesNotExist:
            return Response({'error': 'Контакт не найден'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            contact = Contact.objects.get(id=pk, user=request.user)
            contact.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Contact.DoesNotExist:
            return Response({'error': 'Контакт не найден'}, status=status.HTTP_404_NOT_FOUND)


def index(request):
    return render(request, "index.html")
