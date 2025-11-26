from django.shortcuts import render


def health_tools(request):
    """Client health tools page (calculators are client-side)."""
    user_id = request.session.get("user_id") or request.session.get("user")
    is_logged_in = user_id is not None
    
    return render(request, 'health_tools.html', {
        "is_logged_in": is_logged_in,
        "encouraging_message": "Discover our comprehensive health tools designed to help you monitor and improve your wellbeing. From BMI calculators to health risk assessments, our tools provide valuable insights to support your health journey. Login to save your results and track your progress over time."
    })


