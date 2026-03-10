"""
Django forms for marketplace with validation.
Author: TJ
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Product
from .services.validators import (
    validate_lead_time,
    validate_uk_postcode,
    validate_product_data,
    validate_status_transition,
)


class ProductForm(forms.ModelForm):
    """
    Form for producers to create and edit products.
    Validates price, stock quantity, and other product data.
    """
    
    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'price',
            'unit',
            'stock_quantity',
            'category',
            'is_available',
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe your product...'
            }),
            'price': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'min': '0',
                'placeholder': '0'
            }),
        }
    
    def clean_price(self):
        """Validate that price is greater than 0."""
        price = self.cleaned_data.get('price')
        
        if price is not None and price <= 0:
            raise ValidationError("Price must be greater than 0")
        
        return price
    
    def clean_stock_quantity(self):
        """Validate that stock quantity is not negative."""
        stock_quantity = self.cleaned_data.get('stock_quantity')
        
        if stock_quantity is not None and stock_quantity < 0:
            raise ValidationError("Stock quantity cannot be negative")
        
        return stock_quantity
    
    def clean(self):
        """Cross-field validation for product data."""
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        stock_quantity = cleaned_data.get('stock_quantity')
        
        # Use validator for combined validation
        if price is not None and stock_quantity is not None:
            try:
                validate_product_data(price, stock_quantity)
            except ValidationError as e:
                # Re-raise validation errors
                raise e
        
        return cleaned_data


class CheckoutForm(forms.Form):
    """
    Form for customers to checkout and place orders.
    Validates fulfillment date (48-hour lead time) and delivery details.
    """
    
    fulfillment_date = forms.DateTimeField(
        label="Fulfillment/Delivery Date",
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
        }),
        help_text="Must be at least 48 hours from now"
    )
    
    delivery_address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123 Main Street'
        }),
        help_text="Street address for delivery"
    )
    
    postcode = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'BS1 5JG'
        }),
        help_text="UK postcode format"
    )
    
    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any special delivery instructions...'
        }),
        help_text="Optional delivery notes"
    )
    
    def __init__(self, *args, request=None, **kwargs):
        """
        Initialize form with request to access session cart.
        
        Args:
            request: HttpRequest object to access session
        """
        self.request = request
        super().__init__(*args, **kwargs)
    
    def clean_fulfillment_date(self):
        """Validate that fulfillment date meets 48-hour lead time requirement."""
        fulfillment_date = self.cleaned_data.get('fulfillment_date')
        
        if fulfillment_date:
            try:
                validate_lead_time(fulfillment_date)
            except ValidationError as e:
                raise ValidationError(str(e))
        
        return fulfillment_date
    
    def clean_postcode(self):
        """Validate UK postcode format."""
        postcode = self.cleaned_data.get('postcode')
        
        if postcode:
            try:
                validate_uk_postcode(postcode)
            except ValidationError as e:
                raise ValidationError(str(e))
        
        # Normalize postcode (uppercase, single space)
        return postcode.upper().strip()
    
    def clean_delivery_address(self):
        """Validate delivery address is not empty."""
        delivery_address = self.cleaned_data.get('delivery_address')
        
        if not delivery_address or not delivery_address.strip():
            raise ValidationError("Delivery address cannot be empty")
        
        return delivery_address.strip()
    
    def clean(self):
        """Cross-field validation - check cart is not empty."""
        cleaned_data = super().clean()
        
        # Check if cart exists and is not empty
        if self.request:
            cart = self.request.session.get('cart', {})
            if not cart:
                raise ValidationError(
                    "Your cart is empty. Please add items before checking out."
                )
        
        return cleaned_data


class OrderStatusForm(forms.Form):
    """
    Form for producers to update order status.
    Validates status transitions according to business rules.
    """
    
    STATUS_CHOICES = [
        ('placed', 'Placed'),
        ('paid', 'Paid'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        help_text="Update order status"
    )
    
    def __init__(self, *args, current_status=None, **kwargs):
        """
        Initialize form with current status to filter allowed transitions.
        
        Args:
            current_status (str): Current order status
        """
        self.current_status = current_status
        super().__init__(*args, **kwargs)
        
        # Filter choices based on current status if provided
        if current_status:
            allowed_next_statuses = self._get_allowed_statuses(current_status)
            self.fields['status'].choices = [
                (value, label) for value, label in self.STATUS_CHOICES
                if value in allowed_next_statuses
            ]
    
    def _get_allowed_statuses(self, current_status):
        """
        Get list of allowed next statuses based on current status.
        
        Args:
            current_status (str): Current order status
            
        Returns:
            list: Allowed next statuses
        """
        allowed_transitions = {
            'placed': ['paid', 'cancelled'],
            'paid': ['fulfilled', 'cancelled'],
            'fulfilled': [],  # Terminal state
            'cancelled': [],  # Terminal state
        }
        
        return allowed_transitions.get(current_status, [])
    
    def clean_status(self):
        """Validate that status transition is allowed."""
        new_status = self.cleaned_data.get('status')
        
        # If current status is provided, validate transition
        if self.current_status and new_status:
            try:
                validate_status_transition(self.current_status, new_status)
            except ValidationError as e:
                raise ValidationError(str(e))
        
        return new_status
