from django import forms
from .models import Return, ReturnItem, ReturnImage

class ReturnRequestForm(forms.ModelForm):
   class Meta:
       model = Return
       fields = ['return_type', 'description']  # ← BỎ 'reason'
       widgets = {
           'return_type': forms.Select(attrs={
               'class': 'form-control'
           }),
           'description': forms.Textarea(attrs={
               'class': 'form-control',
               'rows': 4,
               'placeholder': 'Please provide detailed reason for returns (minimum 20 characters)...',
               'required': True
           }),
       }
       labels = {
           'return_type': 'Return Type',
           'description': 'Reason for Return'
       }

class ReturnImageForm(forms.ModelForm):
   class Meta:
       model = ReturnImage
       fields = ['image']
       widgets = {
           'image': forms.ClearableFileInput(attrs={
               'class': 'form-control-file',
               'accept': 'image/*'
           })
       }


class AdminReturnActionForm(forms.Form):
   admin_note = forms.CharField(
       widget=forms.Textarea(attrs={
           'class': 'form-control',
           'rows': 3,
           'placeholder': 'Add note for customer...'
       }),
       required=True
   )
   refund_amount = forms.DecimalField(
       max_digits=10,
       decimal_places=2,
       widget=forms.NumberInput(attrs={
           'class': 'form-control',
           'step': '0.01'
       }),
       required=False
   )

