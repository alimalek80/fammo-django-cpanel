from django import forms
from markdownx.widgets import MarkdownxWidget
from .models import BlogPost

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'slug', 'content', 'category', 'meta_description', 'meta_keywords']
        widgets = {
            'content': MarkdownxWidget()  # ensures editor + uploads on front-end forms
        }