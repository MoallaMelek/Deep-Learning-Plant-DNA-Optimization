from django import forms

from data.dna_loader import EXAMPLE_DNA_SEQUENCE


class SimulationForm(forms.Form):
    dna_sequence = forms.CharField(
        label="DNA sequence",
        widget=forms.Textarea(attrs={"rows": 6}),
        required=False,
        initial=EXAMPLE_DNA_SEQUENCE,
    )
    accession = forms.CharField(label="NCBI accession (optional)", required=False, max_length=60)
    days = forms.IntegerField(label="Simulation days", min_value=30, max_value=120, initial=60)
    use_open_meteo = forms.BooleanField(label="Use Open-Meteo API", required=False, initial=True)

    temperature_c = forms.FloatField(label="Manual temperature (C)", initial=22.0)
    humidity_pct = forms.FloatField(label="Manual humidity (%)", initial=60.0)
    precipitation_mm = forms.FloatField(label="Manual precipitation (mm)", initial=1.5)
    sunlight_hours = forms.FloatField(label="Manual sunlight (hours)", initial=8.0)
    wind_kph = forms.FloatField(label="Manual wind (kph)", initial=10.0)

    auto_train_if_missing = forms.BooleanField(label="Auto-train model if missing", required=False, initial=True)
    generate_gif = forms.BooleanField(label="Generate 3D growth GIF", required=False, initial=True)
