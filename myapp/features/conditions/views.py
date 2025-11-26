from django.shortcuts import render


def conditions(request):
    user_id = request.session.get("user_id") or request.session.get("user")
    is_logged_in = user_id is not None
    
    return render(request, "conditions.html", {
        "is_logged_in": is_logged_in,
        "encouraging_message": "Explore our comprehensive medical conditions database. Learn about symptoms, treatments, and management strategies for various health conditions. Our expert-curated content helps you understand your health better. Login to access personalized condition tracking and receive tailored health recommendations."
    })


