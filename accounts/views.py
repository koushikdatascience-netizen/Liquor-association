from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import ApplicantRegistrationForm


def register(request):
    if request.method == "POST":
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. You can now submit your membership application.")
            return redirect("application_create")
    else:
        form = ApplicantRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})
