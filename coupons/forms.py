from django import forms

class CouponCodeForm(forms.Form):
   code = forms.CharField(
       label="",
       widget=forms.TextInput(attrs={
           "placeholder": "coupon code",
           "class": "form-control",
           "autocomplete": "off",
       })
   )

   def clean_code(self):
       return self.cleaned_data["code"].strip().upper()
