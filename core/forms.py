from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import BankUser, Transaction

class BankUserCreationForm(UserCreationForm):
    class Meta:
        model = BankUser
        fields = ('roll_number', 'name')

class TransferForm(forms.Form):
    recipient_roll_number = forms.CharField(max_length=20, label="Recipient Roll Number")
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=1.00)
    category = forms.ChoiceField(choices=Transaction.CATEGORY_CHOICES, label="Category")

    def clean_recipient_roll_number(self):
        roll = self.cleaned_data['recipient_roll_number']
        try:
            recipient = BankUser.objects.get(roll_number=roll)
            if not recipient.is_active:
                raise forms.ValidationError("Recipient account is not active.")
        except BankUser.DoesNotExist:
            raise forms.ValidationError("Recipient does not exist.")
        return roll
