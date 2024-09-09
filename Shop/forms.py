from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import addressModel,SupportIssue
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class MyLoginForm(forms.Form):
    username = forms.CharField(label="Username")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

    def __init__(self, *args, **kwargs):
        super(MyLoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Sign In'))


class customuserform(UserCreationForm):
    username=forms.CharField(widget=forms.TextInput(attrs={'class':'form-control ','placeholder':'Enter Your Username'}))
    email=forms.CharField(widget=forms.TextInput(attrs={'class':'form-control ','placeholder':'Enter Your Email'}))
    password1=forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control ','placeholder':'Enter Your password'}))
    password2=forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control ','placeholder':'Enter Your conform password'}))
    
    class Meta:
        model = User
        fields = ['username','email','password1','password2']

class addressForm(forms.ModelForm):    
    
     name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'})
    )
     address = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your address'})
    )
     house = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your House or Flat number.'})
    )
     area = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Area,Street'})
    )
     city = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your city'})
    )
     state = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your state'})
    )
     country = forms.ChoiceField(
        choices=[
            ('India', 'India'),
            ('US', 'United States'),
            ('CA', 'Canada'),
            ('GB', 'United Kingdom'),
            ('AU', 'Australia'),
            ('DE', 'Germany'),
            ('FR', 'France'),
            ('JP', 'Japan'),
            ('CN', 'China'),
            ('BR', 'Brazil'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
     zipcode = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your zipcode'})
    )
     phone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your phone number'}),max_length=20
    )
     email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'})
    )
    
     class Meta:
        model = addressModel
        fields = ['name','house','area','address','city','state','country','zipcode','phone','email']
        
class supportForm(forms.ModelForm):
    name=forms.CharField(widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':"Enter your name"}))
    email=forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control', 'placeholder':"Enter your Email ID"}))
    feedback=forms.CharField(widget=forms.Textarea(attrs={'class':'form-control custom-height', 'style':'height:150px;','placeholder':"Please provide the Necessary details."}))
    
    class Meta:
        model = SupportIssue  
        fields = ['name', 'email', 'feedback']