from django import forms
from get_price.constants import partners

class PriceFilterForm(forms.Form):
    partner = forms.ChoiceField(
        label="Партнёр",
        required=False,
        choices=[("", "Все")] + [(str(k), f"{v} ({k})") for k, v in partners.items()],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    date_from = forms.DateTimeField(
        label="с даты",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"})
    )
    date_to = forms.DateTimeField(
        label="по дату",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"})
    )
    item_mode = forms.ChoiceField(
        label="Товары",
        required=False,
        choices=[
            ("all", "Все товары партнёра"),
            ("selected", "Только выбранные артикулы"),
        ],
        initial="all",
        widget=forms.RadioSelect
    )
    item_ids = forms.CharField(
        label="Item ID(ы)",
        required=False,
        help_text="Укажите артикулы через запятую или пробел: 123, 456 789",
        widget=forms.TextInput(attrs={"placeholder": "например: 123, 456 789", "class": "form-control"})
    )
