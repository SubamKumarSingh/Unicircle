# fundraisers/forms.py
from django import forms
from .models import Fundraiser

class FundraiserCreateForm(forms.ModelForm):
    class Meta:
        model = Fundraiser
        fields = ["title", "description", "goal", "image"]
