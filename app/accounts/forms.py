"""
Registration form for customer accounts.
Validates personal information, delivery address, and password.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser
from marketplace.services.validators import validate_uk_postcode


class CustomerRegistrationForm(forms.ModelForm):
    """
    Full registration form for customers.
    Collects name, contact info, delivery address, and password.
    """

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter a secure password'}),
        label="Password",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password'}),
        label="Confirm Password",
    )
    accept_terms = forms.BooleanField(
        required=True,
        label="I accept the terms and conditions",
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'delivery_address',
            'postcode',
            'role',
            'username',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '07700 900123'}),
            'delivery_address': forms.TextInput(attrs={'placeholder': '45 Park Street, Bristol'}),
            'postcode': forms.TextInput(attrs={'placeholder': 'BS1 5JG'}),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email',
            'phone': 'Phone Number',
            'delivery_address': 'Delivery Address',
            'postcode': 'Postcode',
            'role': 'I am a...',
            'username': 'Username',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make these fields required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        # Remove admin from role choices - admin accounts are created via Django admin only
        self.fields['role'].choices = [
            (value, label) for value, label in self.fields['role'].choices
            if value != 'admin'
        ]

    def clean_role(self):
        role = self.cleaned_data.get('role')
        allowed = {
            CustomUser.Role.CUSTOMER,
            CustomUser.Role.PRODUCER,
            CustomUser.Role.COMMUNITY_GROUP,
            CustomUser.Role.RESTAURANT,
        }
        if role not in allowed:
            raise ValidationError("Invalid role selection.")
        return role

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_postcode(self):
        postcode = self.cleaned_data.get('postcode')
        if postcode:
            try:
                validate_uk_postcode(postcode)
            except ValidationError:
                raise ValidationError("Please enter a valid UK postcode (e.g. BS1 5JG).")
            return postcode.upper().strip()
        return postcode

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
