from django import forms
from .models import Pet, AgeCategory, Breed, HealthIssue

BOOLEAN_CHOICES = [(True, 'Yes'), (False, 'No')]

class PetForm(forms.ModelForm):
    neutered = forms.ChoiceField(
        choices=BOOLEAN_CHOICES,
        widget=forms.RadioSelect(),
        required=True,
        label="Is your pet neutered?"
    )

    class Meta:
        model = Pet
        exclude = ['user']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-full shadow-xl',
                'placeholder': 'e.g. Manti'
            }),
            'pet_type': forms.RadioSelect(),  # <-- Use RadioSelect, not Select
            'gender': forms.RadioSelect(),
            'neutered': forms.RadioSelect(),
            'age_category': forms.RadioSelect(),
            'age_years': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md',
                'placeholder': 'Years'
            }),
            'age_months': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md',
                'placeholder': 'Months'
            }),
            'age_weeks': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md',
                'placeholder': 'Weeks'
            }),
            'breed': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-md'}),
            'food_types': forms.CheckboxSelectMultiple(),
            'food_feeling': forms.RadioSelect(),
            'food_importance': forms.RadioSelect(),
            'body_type': forms.RadioSelect(),
            'weight': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-md'}),
            'activity_level': forms.RadioSelect(),
            'food_allergies': forms.CheckboxSelectMultiple(),
            'food_allergy_other': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md'}),
            'health_issues': forms.CheckboxSelectMultiple(),
            'treat_frequency': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = "What is your pet's name?"
        self.fields['pet_type'].label = "What type of pet do you have?"
        self.fields['gender'].label = "Is your pet a girl or a boy?"
        self.fields['age_category'].label = "What is your pet's age category?"
        # Set breed queryset to empty initially for create form
        self.fields['breed'].queryset = Breed.objects.none()

        # If form is bound to data (POST request)
        if 'pet_type' in self.data:
            try:
                pet_type_id = int(self.data.get('pet_type'))
                self.fields['breed'].queryset = Breed.objects.filter(pet_type_id=pet_type_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input, queryset remains empty
        # If form is for an existing instance (edit form, GET request)
        elif self.instance.pk and self.instance.pet_type:
            self.fields['breed'].queryset = self.instance.pet_type.breeds.order_by('name')

        # Remove empty labels
        radio_fields = ['pet_type', 'gender', 'age_category', 'body_type', 'activity_level', 'food_feeling', 'food_importance', 'treat_frequency']
        for field_name in radio_fields:
            if field_name in self.fields:
                self.fields[field_name].empty_label = None


# ============================================================================
# NEW WIZARD FORMS USING SESSIONWIZARDVIEW PATTERN (Step by step implementation)
# ============================================================================

# Step 1 — Pet name and type (following multistep app pattern)
class Step1NameForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ["name", "pet_type"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 text-lg border-2 border-gray-300 rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white",
                "placeholder": "Enter your Pet's Name",
                "style": "background-color: white !important; color: #374151 !important; border-color: #d1d5db !important;",
            }),
            "pet_type": forms.RadioSelect(),
        }
        labels = {
            "name": "What's your Pet's Name?",
            "pet_type": "What is your Pet Type?"
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make both fields required
        self.fields['name'].required = True
        self.fields['name'].error_messages = {
            'required': 'Please enter your pet\'s name before proceeding to the next step.'
        }
        
        # Configure pet_type field
        self.fields['pet_type'].empty_label = None
        self.fields['pet_type'].required = True
        self.fields['pet_type'].error_messages = {
            'required': 'Please select your pet\'s type before proceeding to the next step.'
        }
        
        # Make sure we have PetType objects and configure the field
        from .models import PetType
        self.fields['pet_type'].queryset = PetType.objects.all()
        self.fields['pet_type'].required = True


# Step 2 — Pet gender and neutered status (following multistep app pattern)
class Step2GenderForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ["gender", "neutered"]
        labels = {
            "gender": "Is your Pet a Girl or Boy?",
            "neutered": "Is your Pet neutered/spayed?"
        }
        widgets = {
            "gender": forms.RadioSelect(),
            "neutered": forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Make sure we have Gender objects in the database
        from .models import Gender
        if not Gender.objects.exists():
            Gender.objects.get_or_create(name="Boy")
            Gender.objects.get_or_create(name="Girl")
        
        # Remove the empty choice (blank option)
        self.fields['gender'].empty_label = None
        self.fields['gender'].required = True
        # Ensure we only show Boy and Girl options
        self.fields['gender'].queryset = Gender.objects.all()
        
        # Configure neutered field
        self.fields['neutered'].required = True
        
        # Customize labels based on wizard data if available
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            
            if pet_name:
                # Update gender label with pet name
                self.fields['gender'].label = f"Is {pet_name} a Girl or Boy?"
                self.fields['neutered'].label = f"Is {pet_name} neutered/spayed?"
                
                # Store pet name for use in template
                self.pet_name = pet_name
            else:
                self.pet_name = ""
        else:
            self.pet_name = ""


# Step 3 — Pet age category and specific age (following multistep app pattern)
class Step3AgeForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ["age_category", "age_years", "age_months", "age_weeks"]
        labels = {
            "age_category": "How old is your Pet?",
            "age_years": "Years",
            "age_months": "Months", 
            "age_weeks": "Weeks"
        }
        widgets = {
            "age_category": forms.RadioSelect(),
            "age_years": forms.NumberInput(attrs={
                "class": "input input-bordered w-full",
                "placeholder": "0",
                "min": "0",
                "max": "30"
            }),
            "age_months": forms.NumberInput(attrs={
                "class": "input input-bordered w-full", 
                "placeholder": "0",
                "min": "0",
                "max": "12"  # Will be adjusted by JavaScript
            }),
            "age_weeks": forms.NumberInput(attrs={
                "class": "input input-bordered w-full",
                "placeholder": "0", 
                "min": "0",
                "max": "52"
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference for clean methods
        if wizard:
            self.wizard = wizard
        
        # Configure age_category field
        self.fields['age_category'].empty_label = None
        self.fields['age_category'].required = True
        self.fields['age_category'].error_messages = {
            'required': 'Please select your pet\'s age category before proceeding to the next step.'
        }
        
        # Make age fields not required by default (will be handled by JavaScript)
        self.fields['age_years'].required = False
        self.fields['age_months'].required = False  
        self.fields['age_weeks'].required = False
        
        # Customize labels and filter age categories based on wizard data if available
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            pet_type = step1_data.get('pet_type')
            
            if pet_name:
                # Update label with pet name
                self.fields['age_category'].label = f"How old is {pet_name}?"
                # Store pet name for use in template
                self.pet_name = pet_name
            else:
                self.pet_name = ""
            
            # Filter age categories by pet type
            if pet_type:
                from .models import AgeCategory
                self.fields['age_category'].queryset = AgeCategory.objects.filter(pet_type=pet_type)
                
                # Check if current age_category value is still valid for the new pet_type
                if self.instance and self.instance.age_category:
                    if self.instance.age_category.pet_type != pet_type:
                        # Clear invalid age category when pet type changes
                        self.instance.age_category = None
                        self.instance.age_years = None
                        self.instance.age_months = None
                        self.instance.age_weeks = None
                        
            else:
                # No pet type selected, show all age categories
                from .models import AgeCategory
                self.fields['age_category'].queryset = AgeCategory.objects.all()
        else:
            self.pet_name = ""
            # No wizard, show all age categories
            from .models import AgeCategory
            self.fields['age_category'].queryset = AgeCategory.objects.all()


# Step 4 — Pet breed selection with unknown breed option (following multistep app pattern)
class Step4BreedForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ["breed", "unknown_breed"]
        labels = {
            "breed": "What breed is your pet?",
            "unknown_breed": "I don't know the breed"
        }
        widgets = {
            "breed": forms.Select(attrs={
                "class": "select select-bordered w-full",
                "id": "breed-select"
            }),
            "unknown_breed": forms.CheckboxInput(attrs={
                "class": "checkbox checkbox-primary",
                "id": "unknown-breed-checkbox"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Configure breed field
        self.fields['breed'].empty_label = "Select a breed"
        self.fields['breed'].required = False
        self.fields['unknown_breed'].required = False
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['breed'].label = f"What breed is {pet_name}?"
        
        # Filter breeds based on pet type from step 1
        if wizard:
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_type = step1_data.get('pet_type')
            
            if pet_type:
                # Filter breeds by the selected pet type
                from .models import Breed
                self.fields['breed'].queryset = Breed.objects.filter(pet_type=pet_type).order_by('name')
            else:
                # No pet type selected, show empty queryset
                from .models import Breed
                self.fields['breed'].queryset = Breed.objects.none()
        else:
            # No wizard, show all breeds
            from .models import Breed
            self.fields['breed'].queryset = Breed.objects.all().order_by('name')
    
    def clean(self):
        cleaned_data = super().clean()
        breed = cleaned_data.get('breed')
        unknown_breed = cleaned_data.get('unknown_breed')
        
        # If unknown_breed is checked, breed selection is not required
        if not unknown_breed and not breed:
            raise forms.ValidationError(
                "Please select a breed or check 'I don't know the breed'."
            )
        
        # If unknown_breed is checked, clear the breed selection
        if unknown_breed:
            cleaned_data['breed'] = None
            
        return cleaned_data


# Step 5 — Pet food types selection (following multistep app pattern)
class Step5FoodForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ["food_types"]
        labels = {
            "food_types": "What is your pet currently eating?"
        }
        widgets = {
            "food_types": forms.CheckboxSelectMultiple(attrs={
                "class": "checkbox-group"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference for access to other steps
        if wizard:
            self.wizard = wizard
        
        # Configure food_types field
        self.fields['food_types'].required = True
        self.fields['food_types'].error_messages = {
            'required': 'Please select at least one food type.'
        }
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['food_types'].label = f"What is {pet_name} currently eating?"


# Step 6 — Pet food feeling selection (following multistep app pattern)
class Step6FoodFeelingForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ["food_feeling"]
        labels = {
            "food_feeling": "How does your pet feel about food?"
        }
        widgets = {
            "food_feeling": forms.RadioSelect(attrs={
                "class": "food-feeling-radio"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Configure food_feeling field
        self.fields['food_feeling'].empty_label = None
        self.fields['food_feeling'].required = True
        self.fields['food_feeling'].error_messages = {
            'required': 'Please select how your pet feels about food.'
        }
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['food_feeling'].label = f"How does {pet_name} feel about food?"
        
        # Get food feelings with descriptions for template use
        from .models import FoodFeeling
        self.food_feelings_with_descriptions = list(FoodFeeling.objects.all().values('id', 'name', 'description'))


# Step 7 — Pet food importance selection (following multistep app pattern)
class Step7FoodImportanceForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ["food_importance"]
        labels = {
            "food_importance": "What is the most important thing about your pet's food?"
        }
        widgets = {
            "food_importance": forms.RadioSelect(attrs={
                "class": "food-importance-radio"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Configure food_importance field
        self.fields['food_importance'].empty_label = None
        self.fields['food_importance'].required = True
        self.fields['food_importance'].error_messages = {
            'required': 'Please select what is most important about your pet\'s food.'
        }
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['food_importance'].label = f"What is the most important thing about {pet_name}'s food?"


# Step 8 — Pet body type selection (following multistep app pattern)
class Step8BodyTypeForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ["body_type"]
        labels = {
            "body_type": "What does your pet's body look like?"
        }
        widgets = {
            "body_type": forms.RadioSelect(attrs={
                "class": "body-type-radio"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Configure body_type field
        self.fields['body_type'].empty_label = None
        self.fields['body_type'].required = True
        self.fields['body_type'].error_messages = {
            'required': 'Please select your pet\'s body type.'
        }
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['body_type'].label = f"What does {pet_name}'s body look like?"
        
        # Get body types with descriptions for template use
        from .models import BodyType
        self.body_types_with_descriptions = list(BodyType.objects.all().values('id', 'name', 'description'))


class Step9WeightForm(forms.ModelForm):
    """
    Step 9: Pet Weight
    
    Weight selection with slider and input field
    Following multistep sample pattern exactly
    """
    
    class Meta:
        model = Pet
        fields = ['weight']
        labels = {
            "weight": "How much does your Pet weigh?",
        }
        widgets = {
            "weight": forms.NumberInput(attrs={
                "class": "weight-field",
                "step": "0.1",
                "min": "0",
                "max": "50"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Configure weight field
        self.fields['weight'].required = True
        self.fields['weight'].error_messages = {
            'required': 'Please enter your pet\'s weight.'
        }
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['weight'].label = f"How much does {pet_name} weigh?"


class Step10ActivityLevelForm(forms.ModelForm):
    """
    Step 10: Pet Activity Level
    
    Activity level selection with descriptions
    Following multistep sample pattern exactly
    """
    
    class Meta:
        model = Pet
        fields = ['activity_level']
        labels = {
            "activity_level": "How active is your Pet?",
        }
        widgets = {
            "activity_level": forms.RadioSelect(attrs={
                "class": "activity-level-radio"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Configure activity_level field
        self.fields['activity_level'].empty_label = None
        self.fields['activity_level'].required = True
        self.fields['activity_level'].error_messages = {
            'required': 'Please select your pet\'s activity level.'
        }
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['activity_level'].label = f"How active is {pet_name}?"
        
        # Get activity levels with descriptions for template use
        from .models import ActivityLevel
        self.activity_levels = list(ActivityLevel.objects.all().values('id', 'name', 'description'))


class Step13TreatFrequencyForm(forms.ModelForm):
    """
    Step 13: Pet Treat Frequency
    
    Treat frequency selection with radio buttons
    Following multistep sample pattern exactly
    """
    
    class Meta:
        model = Pet
        fields = ['treat_frequency']
        labels = {
            "treat_frequency": "How often does your Pet get treats?",
        }
        widgets = {
            "treat_frequency": forms.RadioSelect(attrs={
                "class": "treat-frequency-radio"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Configure treat_frequency field
        self.fields['treat_frequency'].empty_label = None
        self.fields['treat_frequency'].required = True
        self.fields['treat_frequency'].error_messages = {
            'required': 'Please select your pet\'s treat frequency.'
        }
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['treat_frequency'].label = f"How often does {pet_name} get treats?"
        
        # Get treat frequencies with descriptions for template use
        from .models import TreatFrequency
        self.treat_frequencies = list(TreatFrequency.objects.all().values('id', 'name', 'description'))


class Step11FoodAllergiesForm(forms.ModelForm):
    """
    Step 11: Pet Food Allergies
    
    Food allergies selection with limit and other allergies text field
    Following multistep sample pattern exactly
    """
    
    class Meta:
        model = Pet
        fields = ['food_allergies', 'food_allergy_other']
        widgets = {
            "food_allergies": forms.CheckboxSelectMultiple(attrs={
                "class": "checkbox-group"
            }),
            "food_allergy_other": forms.Textarea(attrs={
                "class": "textarea textarea-bordered w-full",
                "placeholder": "Describe any other food allergies or sensitivities...",
                "rows": "3"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Configure food_allergies field
        self.fields['food_allergies'].required = False
        self.fields['food_allergies'].help_text = "Select up to 4 allergies"
        
        # Ensure queryset includes all food allergies
        from .models import FoodAllergy
        self.fields['food_allergies'].queryset = FoodAllergy.objects.all().order_by('order', 'name')
        
        # Configure food_allergy_other field
        self.fields['food_allergy_other'].required = False
        self.fields['food_allergy_other'].help_text = "Describe any other allergies not listed above"
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['food_allergies'].label = f"Does {pet_name} have any food allergies or sensitivities?"
            self.fields['food_allergy_other'].label = f"Other allergies not listed (for {pet_name})"
        else:
            self.fields['food_allergies'].label = "Does your pet have any food allergies or sensitivities?"
            self.fields['food_allergy_other'].label = "Other allergies not listed"

    def clean_food_allergies(self):
        """Validate that no more than 4 allergies are selected"""
        food_allergies = self.cleaned_data.get('food_allergies')
        if food_allergies and food_allergies.count() > 4:
            raise forms.ValidationError("Please select no more than 4 food allergies.")
        return food_allergies


class Step12HealthIssuesForm(forms.ModelForm):
    """
    Step 12: Pet Health Issues
    
    Health issues selection with limit 
    Following the same pattern as Step11FoodAllergiesForm
    """
    
    class Meta:
        model = Pet
        fields = ['health_issues']
        widgets = {
            "health_issues": forms.CheckboxSelectMultiple(attrs={
                "class": "checkbox-group"
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Configure health_issues field
        self.fields['health_issues'].required = False
        self.fields['health_issues'].help_text = "Select up to 4 health issues"
        self.fields['health_issues'].queryset = HealthIssue.objects.all().order_by('order', 'name')
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['health_issues'].label = f"Does {pet_name} have any health issues?"
        else:
            self.fields['health_issues'].label = "Does your pet have any health issues?"

    def clean_health_issues(self):
        """Validate that no more than 4 health issues are selected"""
        health_issues = self.cleaned_data.get('health_issues')
        if health_issues and health_issues.count() > 4:
            raise forms.ValidationError("Please select no more than 4 health issues.")
        return health_issues


class Step14EmailForm(forms.Form):
    """
    Step 14: Email Collection (for non-logged-in users)
    
    Collect email address from non-logged-in users before final step
    """
    
    email = forms.EmailField(
        label="Email Address",
        help_text="We'll use this email to send you your pet's personalized report",
        widget=forms.EmailInput(attrs={
            "class": "input input-bordered input-lg w-full text-center",
            "placeholder": "Enter your email address"
        }),
        required=True,
        error_messages={
            'required': 'Please enter your email address.',
            'invalid': 'Please enter a valid email address.'
        }
    )
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['email'].help_text = f"We'll use this email to send you {pet_name}'s personalized report"


class Step15AccountChoiceForm(forms.Form):
    """
    Step 15: Account Creation Choice (for non-logged-in users)
    
    Allow non-logged-in users to choose between creating account or getting test report only
    """
    
    ACCOUNT_CHOICES = [
        ('create_account', 'Create Account & Get Full Report'),
        ('test_report', 'Just Get Test Report (No Account)')
    ]
    
    account_choice = forms.ChoiceField(
        choices=ACCOUNT_CHOICES,
        label="What would you like to do?",
        widget=forms.RadioSelect(attrs={
            "class": "account-choice-radio"
        }),
        required=True,
        error_messages={
            'required': 'Please select an option.'
        }
    )
    
    def __init__(self, *args, **kwargs):
        # Extract wizard instance if passed
        wizard = kwargs.pop('wizard', None)
        super().__init__(*args, **kwargs)
        
        # Store wizard reference
        if wizard:
            self.wizard = wizard
        
        # Get pet name for personalized labels
        pet_name = ""
        if wizard:
            # Get data from step 1
            step1_data = wizard.get_cleaned_data_for_step('step1') or {}
            pet_name = step1_data.get('name', '')
            # Store pet name for use in template
            self.pet_name = pet_name
        else:
            self.pet_name = ""
        
        # Personalize labels if pet name is available
        if pet_name:
            self.fields['account_choice'].label = f"What would you like to do with {pet_name}'s report?"