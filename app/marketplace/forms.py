"""
Django forms for marketplace with validation.
Author: TJ
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Recipe, FarmStory, ProductReview
from .services.validators import (
    validate_lead_time,
    validate_uk_postcode,
    validate_product_data,
    validate_status_transition,
    validate_content_moderation,
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
            'low_stock_threshold',
            'category',
            'is_available',
            'seasonal_status',
            'organic_certification_status',
            'allergen_info',
            'harvest_date',
            'image',
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
            'low_stock_threshold': forms.NumberInput(attrs={
                'min': '0',
                'placeholder': '10'
            }),
            'organic_certification_status': forms.Select(),
            'allergen_info': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g. Contains eggs, milk, gluten'
            }),
            'harvest_date': forms.DateInput(attrs={
                'type': 'date',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['organic_certification_status'].required = False
        self.fields['organic_certification_status'].label = 'Organic Certification'
        self.fields['organic_certification_status'].help_text = 'Select whether this product is Certified Organic or Not Certified.'

        self.fields['allergen_info'].required = True
        self.fields['allergen_info'].help_text = 'List any allergens contained in this product, or state no common allergens.'
        
        # Make low_stock_threshold optional since it has a default value
        self.fields['low_stock_threshold'].required = False
        self.fields['low_stock_threshold'].help_text = 'Alert when stock falls below this level (default: 10)'

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

    def clean_allergen_info(self):
        """Validate that allergen information is always provided."""
        allergen_info = self.cleaned_data.get('allergen_info')

        if not allergen_info or not allergen_info.strip():
            raise ValidationError("Allergen information is required")

        return allergen_info.strip()

    def clean(self):
        """Cross-field validation for product data."""
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        stock_quantity = cleaned_data.get('stock_quantity')

        if price is not None and stock_quantity is not None:
            try:
                validate_product_data(price, stock_quantity)
            except ValidationError as e:
                raise e
        organic_status = cleaned_data.get('organic_certification_status')

        if not organic_status:
            if self.instance and self.instance.pk:
                cleaned_data['organic_certification_status'] = self.instance.organic_certification_status
            else:
                cleaned_data['organic_certification_status'] = Product.OrganicCertificationStatus.NOT_CERTIFIED
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
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('ready', 'Ready for Collection'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        help_text="Update order status"
    )

    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Optional note, e.g. Products will be prepared by delivery date...',
        }),
        help_text="Optional note for the customer"
    )

    def __init__(self, *args, current_status=None, **kwargs):
        """
        Initialize form with current status to filter allowed transitions.

        Args:
            current_status (str): Current order status
        """
        self.current_status = current_status
        super().__init__(*args, **kwargs)

        if current_status:
            allowed_next_statuses = self._get_allowed_statuses(current_status)
            self.fields['status'].choices = [
                (value, label) for value, label in self.STATUS_CHOICES
                if value in allowed_next_statuses or value == current_status
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
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['ready', 'cancelled'],
            'ready': ['delivered', 'cancelled'],
            'delivered': [],
            'cancelled': [],
        }

        return allowed_transitions.get(current_status, [])

    def clean_status(self):
        """Validate that status transition is allowed."""
        new_status = self.cleaned_data.get('status')

        if self.current_status and new_status:
            try:
                validate_status_transition(self.current_status, new_status)
            except ValidationError as e:
                raise ValidationError(str(e))

        return new_status

# Lines 303-503 by Alex McBride
class RecipeForm(forms.ModelForm):
    """Form for producers to create and edit recipes."""
    
    class Meta:
        model = Recipe
        fields = [
            'title',
            'description',
            'ingredients',
            'instructions',
            'image',
            'seasonal_tag',
            'is_published',
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Brief description or introduction to the recipe...'
            }),
            'ingredients': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'List all ingredients, e.g.:\n- 500g Carrots\n- 300g Parsnips\n- 2 Potatoes'
            }),
            'instructions': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Step-by-step cooking instructions...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].help_text = 'Enter a descriptive recipe title'
        self.fields['seasonal_tag'].help_text = 'Tag helps customers find seasonal recipes'
        self.fields['is_published'].help_text = 'Publish this recipe to make it visible to customers'
    
    def clean_title(self):
        """Validate recipe title is not empty and appropriate."""
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise ValidationError("Recipe title is required")
        
        # Apply content moderation
        validate_content_moderation(title, "Recipe title")
        
        return title.strip()
    
    def clean_description(self):
        """Validate description is appropriate if provided."""
        description = self.cleaned_data.get('description', '')
        if description and description.strip():
            validate_content_moderation(description, "Recipe description")
        return description.strip() if description else ''
    
    def clean_ingredients(self):
        """Validate ingredients list is not empty and appropriate."""
        ingredients = self.cleaned_data.get('ingredients')
        if not ingredients or not ingredients.strip():
            raise ValidationError("Ingredients list is required")
        
        # Apply content moderation
        validate_content_moderation(ingredients, "Ingredients list")
        
        return ingredients.strip()
    
    def clean_instructions(self):
        """Validate cooking instructions are not empty and appropriate."""
        instructions = self.cleaned_data.get('instructions')
        if not instructions or not instructions.strip():
            raise ValidationError("Cooking instructions are required")
        
        # Apply content moderation
        validate_content_moderation(instructions, "Cooking instructions")
        
        return instructions.strip()


class FarmStoryForm(forms.ModelForm):
    """Form for producers to create and edit farm stories."""
    
    class Meta:
        model = FarmStory
        fields = [
            'title',
            'content',
            'image',
            'is_published',
        ]
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 10,
                'placeholder': 'Share your farm story...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].help_text = 'Enter a title for your farm story'
        self.fields['content'].help_text = 'Write your story - share insights about your farm, harvest season, or farming practices'
        self.fields['is_published'].help_text = 'Publish this story to make it visible to customers'
    
    def clean_title(self):
        """Validate story title is not empty and appropriate."""
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise ValidationError("Story title is required")
        
        # Apply content moderation
        validate_content_moderation(title, "Story title")
        
        return title.strip()
    
    def clean_content(self):
        """Validate story content is not empty and appropriate."""
        content = self.cleaned_data.get('content')
        if not content or not content.strip():
            raise ValidationError("Story content is required")
        
        # Apply content moderation
        validate_content_moderation(content, "Story content")
        
        return content.strip()


class ProductReviewForm(forms.ModelForm):
    """Form for customers to submit product reviews and ratings."""
    
    class Meta:
        model = ProductReview
        fields = [
            'rating',
            'title',
            'review_text',
            'is_anonymous',
        ]
        widgets = {
            'rating': forms.RadioSelect(choices=[
                (5, '★★★★★ (5 stars)'),
                (4, '★★★★☆ (4 stars)'),
                (3, '★★★☆☆ (3 stars)'),
                (2, '★★☆☆☆ (2 stars)'),
                (1, '★☆☆☆☆ (1 star)'),
            ]),
            'title': forms.TextInput(attrs={
                'placeholder': 'Brief summary of your review',
                'maxlength': '200',
            }),
            'review_text': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Share your experience with this product...',
            }),
            'is_anonymous': forms.CheckboxInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configure field properties
        self.fields['rating'].help_text = 'Rate your experience with this product'
        self.fields['title'].help_text = 'Give your review a brief title'
        self.fields['review_text'].help_text = 'Share details about your experience'
        self.fields['is_anonymous'].help_text = 'Check to hide your name on this review'
        self.fields['is_anonymous'].label = 'Post anonymously'
    
    def clean_title(self):
        """Validate review title is not empty and appropriate."""
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise ValidationError("Review title is required")
        
        # Apply content moderation
        validate_content_moderation(title, "Review title")
        
        return title.strip()
    
    def clean_review_text(self):
        """Validate review text is not empty and appropriate."""
        review_text = self.cleaned_data.get('review_text')
        if not review_text or not review_text.strip():
            raise ValidationError("Review text is required")
        
        # Apply content moderation
        validate_content_moderation(review_text, "Review text")
        
        return review_text.strip()
    
    def clean_rating(self):
        """Validate rating is within allowed range."""
        rating = self.cleaned_data.get('rating')
        if rating is not None and (rating < 1 or rating > 5):
            raise ValidationError("Rating must be between 1 and 5 stars")
        return rating